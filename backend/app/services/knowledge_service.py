import asyncio
import uuid
from collections import Counter
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import ASSISTANT_PROMPTS
from app.db.models.knowledge_document import KnowledgeDocument
from app.schemas.knowledge import KnowledgeSource, KnowledgeStatsResponse
from app.services.document_parser import SUPPORTED_EXTENSIONS
from app.services.embedding_service import embedding_service
from app.services.knowledge_jobs import process_document_job
from app.services.ollama_service import ollama_service
from app.services.vector_store import vector_store

class KnowledgeServiceError(RuntimeError):
    pass

async def queue_document(upload: UploadFile, category: str, uploaded_by: str, db: AsyncSession) -> KnowledgeDocument:
    original_name = Path(upload.filename or "document").name
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise KnowledgeServiceError(f"Unsupported file type: {extension}")

    content = await upload.read()
    if not content:
        raise KnowledgeServiceError("The uploaded document is empty.")
    if len(content) > settings.knowledge_max_file_mb * 1024 * 1024:
        raise KnowledgeServiceError(f"File exceeds {settings.knowledge_max_file_mb} MB.")

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

async def retry_document(document_id: uuid.UUID, db: AsyncSession) -> KnowledgeDocument:
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

async def get_document(document_id: uuid.UUID, db: AsyncSession) -> KnowledgeDocument:
    record = await db.get(KnowledgeDocument, document_id)
    if record is None:
        raise KnowledgeServiceError("Knowledge document not found.")
    return record

async def list_documents(db: AsyncSession) -> list[KnowledgeDocument]:
    result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    )
    return list(result.scalars().all())

async def get_stats(db: AsyncSession) -> KnowledgeStatsResponse:
    documents = await list_documents(db)
    categories = Counter(item.category for item in documents)
    return KnowledgeStatsResponse(
        total_documents=len(documents),
        ready_documents=sum(item.status == "ready" for item in documents),
        failed_documents=sum(item.status == "failed" for item in documents),
        processing_documents=sum(item.status in {"queued", "processing"} for item in documents),
        total_chunks=sum(item.chunk_count for item in documents),
        categories=dict(sorted(categories.items())),
    )

async def delete_document(document_id: uuid.UUID, db: AsyncSession) -> None:
    record = await db.get(KnowledgeDocument, document_id)
    if record is None:
        raise KnowledgeServiceError("Knowledge document not found.")
    if record.status in {"queued", "processing"}:
        raise KnowledgeServiceError("Wait for processing to finish before deleting.")
    await vector_store.delete_document(str(record.id))
    path = Path(record.stored_path)
    if path.exists() and path.is_file():
        path.unlink()
    await db.delete(record)
    await db.commit()

async def search_knowledge(query: str, top_k: int, category: str | None) -> list[KnowledgeSource]:
    embedding = (await embedding_service.embed([query]))[0]
    return await vector_store.search(embedding, top_k, category)

async def answer_with_knowledge(question: str, top_k: int, category: str | None, assistant: str) -> tuple[str, list[KnowledgeSource]]:
    sources = await search_knowledge(question, top_k, category)
    if not sources:
        return "I could not find relevant approved company knowledge.", []

    context = []
    for index, source in enumerate(sources, 1):
        page = f", page {source.page_number}" if source.page_number else ""
        context.append(f"[Source {index}] {source.filename}{page}\n{source.text}")

    system_prompt = ASSISTANT_PROMPTS.get(assistant, ASSISTANT_PROMPTS["general"]).strip()
    messages = [
        {
            "role": "system",
            "content": (
                f"{system_prompt}\n\nAnswer only from approved company context. "
                "If insufficient, say so. Cite [Source 1], [Source 2], etc."
            ),
        },
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nApproved context:\n\n" + "\n\n".join(context),
        },
    ]
    return await ollama_service.chat(messages), sources
