import asyncio
import uuid
from collections import Counter
from contextlib import nullcontext
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import ASSISTANT_PROMPTS
from app.db.models.knowledge_document import KnowledgeDocument
from app.db.models.user import User
from app.schemas.context import ContextMetadata
from app.schemas.knowledge import KnowledgeSource, KnowledgeStatsResponse
from app.services.context_engine import context_engine
from app.services.document_parser import SUPPORTED_EXTENSIONS
from app.services.embedding_service import embedding_service
from app.services.intelligence_router import intelligence_router
from app.services.knowledge_jobs import process_document_job
from app.services.ollama_service import ollama_service
from app.services.performance_instrumentation import AskPerformanceInstrumentation
from app.services.vector_store import vector_store


class KnowledgeServiceError(RuntimeError):
    pass


async def queue_document(upload, category, uploaded_by, db):
    original_name = Path(upload.filename or "document").name
    extension = Path(original_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise KnowledgeServiceError(f"Unsupported file type: {extension}")

    content = await upload.read()
    if not content:
        raise KnowledgeServiceError("The uploaded document is empty.")

    if len(content) > settings.knowledge_max_file_mb * 1024 * 1024:
        raise KnowledgeServiceError(
            f"File exceeds {settings.knowledge_max_file_mb} MB."
        )

    document_id = uuid.uuid4()
    upload_dir = Path(settings.knowledge_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{document_id}{extension}"
    stored_path.write_bytes(content)

    record = KnowledgeDocument(
        id=document_id,
        filename=original_name,
        stored_path=str(stored_path),
        content_type=upload.content_type or "application/octet-stream",
        category=category.strip().lower() or "general",
        uploaded_by=uploaded_by,
        status="queued",
        stage="queued",
        progress_percent=0,
        page_count=0,
        pages_processed=0,
        ocr_pages=0,
        chunk_count=0,
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)
    asyncio.create_task(process_document_job(record.id))
    return record


async def retry_document(document_id, db):
    record = await db.get(KnowledgeDocument, document_id)
    if record is None:
        raise KnowledgeServiceError("Knowledge document not found.")
    if record.status in {"queued", "processing"}:
        raise KnowledgeServiceError("Document is already being processed.")

    record.status = "queued"
    record.stage = "queued"
    record.progress_percent = 0
    record.error_message = None
    await db.commit()
    await db.refresh(record)
    asyncio.create_task(process_document_job(record.id))
    return record


async def get_document(document_id, db):
    record = await db.get(KnowledgeDocument, document_id)
    if record is None:
        raise KnowledgeServiceError("Knowledge document not found.")
    return record


async def list_documents(db):
    result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    )
    return list(result.scalars().all())


async def get_stats(db):
    documents = await list_documents(db)
    categories = Counter(item.category for item in documents)

    return KnowledgeStatsResponse(
        total_documents=len(documents),
        ready_documents=sum(item.status == "ready" for item in documents),
        failed_documents=sum(item.status == "failed" for item in documents),
        processing_documents=sum(
            item.status in {"queued", "processing"} for item in documents
        ),
        total_chunks=sum(item.chunk_count for item in documents),
        categories=dict(sorted(categories.items())),
    )


async def delete_document(document_id, db):
    record = await db.get(KnowledgeDocument, document_id)
    if record is None:
        raise KnowledgeServiceError("Knowledge document not found.")
    if record.status in {"queued", "processing"}:
        raise KnowledgeServiceError(
            "Wait for processing to finish before deleting."
        )

    await vector_store.delete_document(str(record.id))
    path = Path(record.stored_path)
    if path.exists() and path.is_file():
        path.unlink()

    await db.delete(record)
    await db.commit()


async def search_knowledge(
    query,
    top_k,
    category,
    instrumentation: AskPerformanceInstrumentation | None = None,
):
    embedding_timer = (
        instrumentation.measure("embedding_ms")
        if instrumentation
        else nullcontext()
    )
    with embedding_timer:
        embedding = (await embedding_service.embed([query]))[0]

    search_timer = (
        instrumentation.measure("qdrant_vector_search_ms")
        if instrumentation
        else nullcontext()
    )
    with search_timer:
        return await vector_store.search(embedding, top_k, category)


async def _search_routed_collections(
    question,
    top_k,
    collections,
    instrumentation: AskPerformanceInstrumentation | None = None,
):
    if not collections:
        return []

    merged: list[KnowledgeSource] = []
    seen: set[tuple[str, int]] = set()

    per_collection = max(2, min(top_k, 4))

    for collection in collections:
        started_at = instrumentation.clock() if instrumentation else 0.0
        collection_sources = await search_knowledge(
            question,
            per_collection,
            collection,
            instrumentation,
        )
        if instrumentation:
            instrumentation.record_collection_search(
                collection,
                instrumentation.clock() - started_at,
                len(collection_sources),
            )

        for source in collection_sources:
            key = (source.document_id, source.chunk_index)
            if key not in seen:
                seen.add(key)
                merged.append(source)

    merged.sort(key=lambda source: source.score, reverse=True)
    return merged[:top_k]


async def answer_with_knowledge(
    question,
    top_k,
    category,
    assistant,
    use_employee_context,
    current_user,
    db,
    instrumentation: AskPerformanceInstrumentation | None = None,
    model_override: str | None = None,
):
    router_timer = (
        instrumentation.measure("intelligence_router")
        if instrumentation
        else nullcontext()
    )
    with router_timer:
        route = intelligence_router.route(question)

    if category:
        routed_collections = [category]
    else:
        routed_collections = route.collections

    if instrumentation:
        instrumentation.record_route(
            route.intent,
            route.confidence,
            routed_collections,
        )

    retrieval_timer = (
        instrumentation.measure("knowledge_retrieval")
        if instrumentation
        else nullcontext()
    )
    with retrieval_timer:
        sources = await _search_routed_collections(
            question,
            top_k,
            routed_collections,
            instrumentation,
        )
    if instrumentation:
        instrumentation.retrieved_chunk_count = len(sources)

    approved_context: list[str] = []

    for index, source in enumerate(sources, 1):
        page = f", page {source.page_number}" if source.page_number else ""
        approved_context.append(
            f"[Source {index}] {source.filename}{page}\n{source.text}"
        )

    personalization = ContextMetadata(
        routed_intent=route.intent,
        routing_confidence=route.confidence,
        routed_collections=routed_collections,
        intelligence_sources=route.sources,
    )
    assembled_context = ""

    if use_employee_context:
        employee_context_timer = (
            instrumentation.measure("employee_context")
            if instrumentation
            else nullcontext()
        )
        with employee_context_timer:
            bundle = await context_engine.build_employee_context(
                db,
                current_user,
                question=question,
                route=route,
                instrumentation=instrumentation,
            )
        assembled_context = f"\n\n{bundle.system_context}"
        personalization = bundle.metadata
        if instrumentation:
            instrumentation.operational_task_count = (
                personalization.operational_tasks_used
            )

    if not sources and not personalization.operational_context_applied:
        fallback_answer = (
            "I could not find relevant approved company knowledge for this request."
        )
        if instrumentation:
            instrumentation.record_answer(fallback_answer)
        return (
            fallback_answer,
            [],
            personalization,
        )

    prompt_timer = (
        instrumentation.measure("prompt_builder")
        if instrumentation
        else nullcontext()
    )
    with prompt_timer:
        knowledge_text = (
            "\n\n".join(approved_context)
            if approved_context
            else "No Knowledge Center documents were selected for this routed request."
        )

        base_prompt = ASSISTANT_PROMPTS.get(
            assistant,
            ASSISTANT_PROMPTS["general"],
        ).strip()

        system_prompt = (
            f"{base_prompt}\n\n"
            f"Routed intent: {route.intent}. "
            f"Routing confidence: {route.confidence:.2f}. "
            "Use only the routed sources supplied below. "
            "Cite documents as [Source 1], [Source 2], and so on. "
            "Cite monday.com records as [Monday Task 1], [Monday Task 2], and so on. "
            "If the routed evidence is insufficient, say so."
            f"{assembled_context}"
        )
        user_prompt = (
            f"Question:\n{question}\n\n"
            f"Routed Knowledge Center context:\n\n{knowledge_text}"
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
        if instrumentation:
            instrumentation.record_prompt(
                messages,
                system_prompt=system_prompt,
                knowledge_context=knowledge_text,
                user_question=question,
            )

    ollama_timer = (
        instrumentation.measure("ollama_total")
        if instrumentation
        else nullcontext()
    )
    with ollama_timer:
        if instrumentation:
            instrumentation.model_name = model_override or settings.ollama_model
        if instrumentation:
            answer, ollama_payload = await ollama_service.chat(
                messages,
                model=model_override,
                return_metadata=True,
            )
            instrumentation.record_ollama_metrics(ollama_payload)
        else:
            answer = await ollama_service.chat(messages, model=model_override)

    if instrumentation:
        instrumentation.record_answer(answer)

    return answer, sources, personalization
