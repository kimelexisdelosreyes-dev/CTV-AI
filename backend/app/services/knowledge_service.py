import asyncio
import uuid
from collections import Counter
from contextlib import nullcontext
from dataclasses import dataclass, replace
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.context_requirements import ContextRequirements
from app.core.knowledge_category_aliases import resolve_category_alias
from app.core.prompts import ASSISTANT_PROMPTS
from app.db.models.knowledge_document import KnowledgeDocument
from app.db.models.user import User
from app.schemas.context import ContextMetadata
from app.schemas.knowledge import KnowledgeSource, KnowledgeStatsResponse
from app.services.context_retrieval_coordinator import context_retrieval_coordinator
from app.services.document_parser import SUPPORTED_EXTENSIONS
from app.services.embedding_service import embedding_service
from app.services.intelligence_router import intelligence_router
from app.services.inference_queue import (
    InferencePriority,
    InferenceQueueError,
    inference_queue,
)
from app.services.knowledge_jobs import process_document_job
from app.services.model_router import (
    ModelRoutingDecision,
    ModelRoutingInput,
    model_router,
)
from app.services.ollama_service import OllamaInferenceTimeoutError, ollama_service
from app.services.performance_instrumentation import (
    AskPerformanceInstrumentation,
    estimate_input_tokens,
    prompt_character_count,
)
from app.services.semantic_cache import SemanticCacheResult, semantic_cache
from app.services.vector_store import vector_store
from app.supervisor.execution_engine import SupervisorEventCallback
from app.supervisor.schemas import RequestedSupervisorMode, SupervisorResult
from app.supervisor.service import executive_supervisor


class KnowledgeServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedKnowledgeAnswer:
    messages: list[dict[str, str]]
    sources: list[KnowledgeSource]
    personalization: ContextMetadata
    model_override: str | None
    model_routing: ModelRoutingDecision | None = None
    fallback_answer: str | None = None
    cached_answer: str | None = None
    cache_result: SemanticCacheResult | None = None
    supervised_answer: str | None = None
    supervisor_result: SupervisorResult | None = None


def _cap_text(value: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(value) <= max_chars:
        return value, False
    if max_chars <= 20:
        return value[:max_chars], True
    return value[: max_chars - 15].rstrip() + "\n[Truncated]", True


def _compact_whitespace(value: str) -> str:
    return " ".join(value.split())


def _knowledge_key(source: KnowledgeSource) -> str:
    return _compact_whitespace(source.text).lower()[:500]


def _select_knowledge_sources(
    sources: list[KnowledgeSource],
    requirements: ContextRequirements,
) -> tuple[list[KnowledgeSource], str, dict[str, int], list[str]]:
    selected: list[KnowledgeSource] = []
    seen: set[str] = set()
    truncated: list[str] = []

    for source in sources:
        key = _knowledge_key(source)
        if key in seen:
            continue
        seen.add(key)
        selected.append(source)
        if len(selected) >= requirements.max_knowledge_chunks:
            break

    original_text = "\n\n".join(source.text for source in selected)
    remaining_chars = requirements.max_knowledge_chars
    context_parts: list[str] = []
    final_sources: list[KnowledgeSource] = []

    for index, source in enumerate(selected, 1):
        if remaining_chars <= 0:
            break
        page = f", page {source.page_number}" if source.page_number else ""
        body = _compact_whitespace(source.text)
        prefix = f"[Source {index}] {source.filename}{page}\n"
        available = max(0, remaining_chars - len(prefix) - 2)
        if available <= 0:
            break
        body, was_truncated = _cap_text(body, available)
        if was_truncated:
            truncated.append("knowledge")
        part = f"{prefix}{body}"
        context_parts.append(part)
        final_sources.append(source)
        remaining_chars -= len(part) + 2

    text = "\n\n".join(context_parts)
    stats = {
        "knowledge_context_original_chars": len(original_text),
        "knowledge_context_final_chars": len(text),
        "knowledge_chunks_original": len(sources),
        "knowledge_chunks_final": len(final_sources),
    }
    return final_sources, text, stats, truncated


def _compose_prompt_sections(
    sections: list[tuple[str, str]],
) -> str:
    return "\n\n".join(
        f"{heading}\n{content.strip()}"
        for heading, content in sections
        if content.strip()
    )


def _apply_total_prompt_budget(
    *,
    system_prompt: str,
    sections: list[tuple[str, str]],
    question: str,
    max_chars: int,
) -> tuple[list[tuple[str, str]], list[str], bool]:
    if max_chars <= 0:
        return sections, [], False

    def current_size(items: list[tuple[str, str]]) -> int:
        user_prompt = (
            f"Question\n{question}\n\n"
            f"{_compose_prompt_sections(items)}"
        )
        return len(system_prompt) + len(user_prompt)

    if current_size(sections) <= max_chars:
        return sections, [], False

    adjusted = list(sections)
    truncated: list[str] = []
    reduction_order = [
        "Conversation History",
        "Employee Context",
        "Operational Context",
        "Knowledge Context",
    ]

    for heading in reduction_order:
        if current_size(adjusted) <= max_chars:
            break
        for index, (section_heading, content) in enumerate(adjusted):
            if section_heading != heading or not content:
                continue
            overflow = current_size(adjusted) - max_chars
            target_size = max(200, len(content) - overflow)
            adjusted_content, was_truncated = _cap_text(content, target_size)
            adjusted[index] = (section_heading, adjusted_content)
            if was_truncated:
                truncated.append(section_heading.lower().replace(" ", "_"))

    return adjusted, truncated, True


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

    merged: list[KnowledgeSource] = []
    seen: set[tuple[str, int]] = set()
    resolved_categories = resolve_category_alias(category)

    search_timer = (
        instrumentation.measure("qdrant_vector_search_ms")
        if instrumentation
        else nullcontext()
    )
    with search_timer:
        for resolved_category in resolved_categories:
            sources = await vector_store.search(embedding, top_k, resolved_category)
            for source in sources:
                key = (source.document_id, source.chunk_index)
                if key not in seen:
                    seen.add(key)
                    merged.append(source)

    merged.sort(key=lambda source: source.score, reverse=True)
    return merged[:top_k]


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
            resolved = ",".join(
                category or "all"
                for category in resolve_category_alias(collection)
            )
            instrumentation.record_collection_search(
                collection,
                instrumentation.clock() - started_at,
                len(collection_sources),
                resolved,
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
    conversation_id: uuid.UUID | None = None,
    prepare_for_stream: bool = False,
    inference_priority: InferencePriority | None = None,
    supervisor_mode: RequestedSupervisorMode = "auto",
    supervisor_event_callback: SupervisorEventCallback | None = None,
) -> tuple[str, list[KnowledgeSource], ContextMetadata] | PreparedKnowledgeAnswer:
    router_timer = (
        instrumentation.measure("intelligence_router")
        if instrumentation
        else nullcontext()
    )
    with router_timer:
        route = intelligence_router.route(question)
    requirements = route.context_requirements

    if category:
        routed_collections = [category]
        requirements = replace(
            requirements,
            include_knowledge=True,
            knowledge_collections=routed_collections,
        )
    else:
        routed_collections = requirements.knowledge_collections

    if not use_employee_context:
        requirements = replace(requirements, include_employee=False)
    if conversation_id is not None:
        requirements = replace(requirements, include_history=True)

    if instrumentation:
        instrumentation.record_context_requirements(requirements)
        instrumentation.record_route(
            route.intent,
            route.confidence,
            routed_collections,
        )

    cache_result = SemanticCacheResult(skip_reason="cache_lookup_failed")
    cache_started = instrumentation.clock() if instrumentation else None
    try:
        cache_lookup = await semantic_cache.build_lookup(
            question=question,
            route_intent=route.intent,
            requirements=requirements,
            current_user_id=current_user.id,
            conversation_id=conversation_id,
            assistant=assistant,
            category=category,
        )
        cache_result = await semantic_cache.lookup(cache_lookup)
    except Exception:
        cache_result = SemanticCacheResult(skip_reason="cache_service_error")
    if instrumentation:
        instrumentation.record_metric("semantic_cache_enabled", settings.ctv_one_semantic_cache_enabled)
        instrumentation.record_metric(
            "semantic_cache_eligible",
            bool(cache_result.lookup and cache_result.lookup.eligible),
        )
        instrumentation.record_metric("semantic_cache_skip_reason", cache_result.skip_reason)
        instrumentation.record_metric("semantic_cache_hit", cache_result.hit)
        instrumentation.record_metric("semantic_cache_hit_type", cache_result.hit_type)
        instrumentation.record_metric("semantic_cache_similarity", cache_result.similarity_score)
        instrumentation.record_metric(
            "semantic_cache_lookup_duration_ms",
            cache_result.lookup_duration_ms
            or max((instrumentation.clock() - cache_started) * 1000, 0.0),
        )
        instrumentation.record_metric(
            "semantic_cache_scope",
            cache_result.lookup.scope_type if cache_result.lookup else None,
        )
        instrumentation.record_metric("ollama_skipped_due_to_cache", cache_result.hit)
        instrumentation.record_metric("semantic_cache_entry_age_seconds", cache_result.age_seconds)
    if cache_result.hit and cache_result.answer and cache_result.personalization:
        inference_queue.record_cache_bypass(instrumentation)
        executive_supervisor.record_cache_hit(instrumentation)
        cached_sources = list(cache_result.sources)
        if instrumentation:
            instrumentation.model_name = cache_result.selected_model
            instrumentation.retrieved_chunk_count = len(cached_sources)
            instrumentation.record_answer(cache_result.answer)
        if prepare_for_stream:
            return PreparedKnowledgeAnswer(
                messages=[],
                sources=cached_sources,
                personalization=cache_result.personalization,
                model_override=cache_result.selected_model,
                cached_answer=cache_result.answer,
                cache_result=cache_result,
            )
        return cache_result.answer, cached_sources, cache_result.personalization

    supervisor_outcome = await executive_supervisor.execute_if_needed(
        question=question,
        requested_mode=supervisor_mode,
        request_id=(instrumentation.request_id if instrumentation else str(uuid.uuid4())),
        conversation_id=str(conversation_id) if conversation_id else None,
        streaming=prepare_for_stream,
        route=route,
        requirements=requirements,
        current_user=current_user,
        db=db,
        top_k=top_k,
        instrumentation=instrumentation,
        knowledge_fetcher=_search_routed_collections,
        event_callback=supervisor_event_callback,
    )
    if supervisor_outcome.result is not None:
        supervisor_result = supervisor_outcome.result
        supervised_sources = _sources_from_supervisor(supervisor_result)
        personalization = ContextMetadata(
            routed_intent=route.intent,
            routing_confidence=route.confidence,
            routed_collections=routed_collections,
            intelligence_sources=route.sources,
            operational_context_applied=any(
                result.agent_id == "operations_agent" and result.status == "success"
                for result in supervisor_result.task_results
            ),
        )
        if instrumentation:
            instrumentation.retrieved_chunk_count = len(supervised_sources)
            instrumentation.record_answer(supervisor_result.final_answer)
        if prepare_for_stream:
            return PreparedKnowledgeAnswer(
                messages=[],
                sources=supervised_sources,
                personalization=personalization,
                model_override=None,
                supervised_answer=supervisor_result.final_answer,
                supervisor_result=supervisor_result,
            )
        return supervisor_result.final_answer, supervised_sources, personalization

    retrieval_timer = (
        instrumentation.measure("context_retrieval")
        if instrumentation
        else nullcontext()
    )
    with retrieval_timer:
        retrieval = await context_retrieval_coordinator.retrieve(
            question=question,
            top_k=top_k,
            routed_collections=routed_collections,
            requirements=requirements,
            route=route,
            current_user=current_user,
            db=db,
            conversation_id=conversation_id,
            knowledge_fetcher=_search_routed_collections,
            instrumentation=instrumentation,
        )
    sources = retrieval.knowledge
    if instrumentation:
        instrumentation.retrieved_chunk_count = len(sources)

    sources, knowledge_text, knowledge_stats, knowledge_truncated = (
        _select_knowledge_sources(sources, requirements)
        if requirements.include_knowledge
        else (
            [],
            "",
            {
                "knowledge_context_original_chars": 0,
                "knowledge_context_final_chars": 0,
                "knowledge_chunks_original": 0,
                "knowledge_chunks_final": 0,
            },
            [],
        )
    )
    if instrumentation:
        for metric_name, metric_value in knowledge_stats.items():
            instrumentation.record_metric(metric_name, metric_value)
        instrumentation.retrieved_chunk_count = len(sources)

    personalization = ContextMetadata(
        routed_intent=route.intent,
        routing_confidence=route.confidence,
        routed_collections=routed_collections,
        intelligence_sources=route.sources,
    )
    employee_context = ""
    operations_text = ""
    operational_original_chars = 0
    operational_final_chars = 0
    operational_tasks_original = 0
    operational_tasks_final = 0
    prompt_truncated = list(knowledge_truncated)
    prompt_omitted: list[str] = []

    if requirements.include_employee and retrieval.employee is not None:
        employee_context = retrieval.employee.system_context
        personalization = retrieval.employee.metadata
    else:
        prompt_omitted.append("employee")

    if requirements.include_operations and retrieval.operations is not None:
        operations = retrieval.operations
        operations_text = operations.text
        operational_original_chars = operations.original_chars
        operational_final_chars = operations.final_chars
        operational_tasks_original = operations.original_task_count
        operational_tasks_final = operations.task_count
        personalization.operational_context_applied = operations.applied
        personalization.operational_tasks_used = operations.task_count
        personalization.operational_boards_used = operations.board_count
        personalization.operational_summary = operations.summary
        if operations.truncated:
            prompt_truncated.append("operations")
        if instrumentation:
            instrumentation.operational_task_count = operations.task_count
    else:
        prompt_omitted.append("operations")

    if not requirements.include_knowledge:
        prompt_omitted.append("knowledge")
    history_text = retrieval.history
    if not requirements.include_history or not history_text:
        prompt_omitted.append("history")

    personalization.context_degraded = retrieval.context_degraded
    personalization.unavailable_context_components = (
        retrieval.unavailable_context_components
    )
    personalization.required_context_failure = retrieval.required_context_failure

    if not sources and not personalization.operational_context_applied:
        if requirements.include_employee:
            pass
        else:
            fallback_answer = (
                "I could not find relevant approved company knowledge for this request."
            )
            if instrumentation:
                instrumentation.record_answer(fallback_answer)
            if prepare_for_stream:
                return PreparedKnowledgeAnswer(
                    messages=[],
                    sources=[],
                    personalization=personalization,
                    model_override=model_override,
                    fallback_answer=fallback_answer,
                    cache_result=cache_result,
                )
            return (
                fallback_answer,
                [],
                personalization,
            )

    if requirements.include_knowledge and not sources:
        fallback_answer = (
            "I could not find relevant approved company knowledge for this request."
        )
        if instrumentation:
            instrumentation.record_answer(fallback_answer)
        if prepare_for_stream:
            return PreparedKnowledgeAnswer(
                messages=[],
                sources=[],
                personalization=personalization,
                model_override=model_override,
                fallback_answer=fallback_answer,
                cache_result=cache_result,
            )
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
        base_prompt = ASSISTANT_PROMPTS.get(
            assistant,
            ASSISTANT_PROMPTS["general"],
        ).strip()

        citation_rules = []
        if knowledge_text:
            citation_rules.append("Cite documents as [Source 1], [Source 2].")
        if operations_text:
            citation_rules.append(
                "Cite monday.com records as [Monday Task 1], [Monday Task 2]."
            )

        system_prompt = "\n".join(
            part
            for part in (
                base_prompt,
                f"Routed intent: {route.intent}; confidence: {route.confidence:.2f}.",
                "Use only the supplied context. If it is insufficient, say so.",
                " ".join(citation_rules),
            )
            if part
        )
        sections = [
            ("Knowledge Context", knowledge_text),
            ("Operational Context", operations_text),
            ("Employee Context", employee_context),
            ("Conversation History", history_text),
        ]
        sections, total_truncated, budget_applied = _apply_total_prompt_budget(
            system_prompt=system_prompt,
            sections=sections,
            question=question,
            max_chars=requirements.max_total_prompt_chars,
        )
        prompt_truncated.extend(total_truncated)
        context_prompt = _compose_prompt_sections(sections)
        user_prompt = (
            f"Question\n{question}\n\n"
            f"{context_prompt}"
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
            instrumentation.record_metric(
                "operational_context_original_chars",
                operational_original_chars,
            )
            instrumentation.record_metric(
                "operational_context_final_chars",
                operational_final_chars,
            )
            instrumentation.record_metric(
                "operational_tasks_original",
                operational_tasks_original,
            )
            instrumentation.record_metric(
                "operational_tasks_final",
                operational_tasks_final,
            )
            instrumentation.record_metric("history_original_chars", len(history_text))
            instrumentation.record_metric("history_final_chars", len(history_text))
            instrumentation.record_metric(
                "history_messages_original",
                len(history_text.splitlines()) if history_text else 0,
            )
            instrumentation.record_metric(
                "history_messages_final",
                len(history_text.splitlines()) if history_text else 0,
            )
            instrumentation.record_prompt(
                messages,
                system_prompt=system_prompt,
                knowledge_context=next(
                    (content for heading, content in sections if heading == "Knowledge Context"),
                    "",
                ),
                operational_context=next(
                    (content for heading, content in sections if heading == "Operational Context"),
                    "",
                ),
                employee_context=next(
                    (content for heading, content in sections if heading == "Employee Context"),
                    "",
                ),
                history_context=next(
                    (content for heading, content in sections if heading == "Conversation History"),
                    "",
                ),
                user_question=question,
            )
            instrumentation.record_prompt_budget(
                applied=budget_applied or bool(prompt_truncated),
                omitted=sorted(set(prompt_omitted)),
                truncated=sorted(set(prompt_truncated)),
            )

    final_prompt_chars = prompt_character_count(messages)
    routing_decision = await model_router.route(
        ModelRoutingInput(
            question=question,
            intent=route.intent,
            include_knowledge=requirements.include_knowledge,
            include_operations=requirements.include_operations,
            include_employee=requirements.include_employee,
            source_count=len(sources),
            operations_task_count=operational_tasks_final,
            final_prompt_chars=final_prompt_chars,
            estimated_prompt_tokens=estimate_input_tokens(final_prompt_chars),
            streaming=prepare_for_stream,
            explicit_model=model_override,
        )
    )
    selected_model = routing_decision.selected_model
    if instrumentation:
        instrumentation.record_model_routing(routing_decision)

    if prepare_for_stream:
        return PreparedKnowledgeAnswer(
            messages=messages,
            sources=sources,
            personalization=personalization,
            model_override=selected_model,
            model_routing=routing_decision,
            cache_result=cache_result,
        )

    if isinstance(db, AsyncSession) and db.in_transaction():
        # Retrieval may autobegin a read transaction. Never retain it while queued.
        await db.rollback()
    admission = await inference_queue.submit(
        request_id=instrumentation.request_id if instrumentation else None,
        user_id=str(
            getattr(
                current_user,
                "id",
                instrumentation.request_id if instrumentation else uuid.uuid4(),
            )
        ),
        conversation_id=str(conversation_id) if conversation_id else None,
        model_name=selected_model,
        model_role=routing_decision.model_role,
        priority=inference_priority,
        streaming=False,
        estimated_cost_class=routing_decision.model_role,
    )
    inference_queue.record_result(instrumentation, admission.initial_result)
    try:
        lease = await admission.wait()
    except InferenceQueueError as exc:
        if exc.result is not None:
            inference_queue.record_result(instrumentation, exc.result)
        raise
    inference_queue.record_lease(instrumentation, lease)

    ollama_timer = (
        instrumentation.measure("ollama_total")
        if instrumentation
        else nullcontext()
    )
    cancelled = False
    try:
        with ollama_timer:
            if instrumentation:
                instrumentation.record_inference_start()
            try:
                async with asyncio.timeout(
                    inference_queue.config.default_timeout_seconds
                ):
                    if instrumentation:
                        answer, ollama_payload = await ollama_service.chat(
                            messages,
                            model=selected_model,
                            return_metadata=True,
                        )
                        instrumentation.record_ollama_metrics(ollama_payload)
                    else:
                        answer = await ollama_service.chat(
                            messages,
                            model=selected_model,
                        )
            except TimeoutError as exc:
                if instrumentation:
                    instrumentation.record_metric("inference_timed_out", True)
                raise OllamaInferenceTimeoutError() from exc
    except asyncio.CancelledError:
        cancelled = True
        if instrumentation:
            instrumentation.record_metric("inference_cancelled", True)
        raise
    finally:
        lease_duration_ms = await lease.release(cancelled=cancelled)
        if instrumentation:
            instrumentation.record_metric(
                "inference_lease_duration_ms",
                lease_duration_ms,
            )

    if instrumentation:
        instrumentation.record_answer(answer)

    write_started = instrumentation.clock() if instrumentation else None
    try:
        stored = await semantic_cache.store(
            result=cache_result,
            answer=answer,
            sources=sources,
            personalization=personalization,
            selected_model=selected_model,
            model_role=routing_decision.model_role,
            result_type="generated_answer",
        )
    except Exception:
        stored = False
    if instrumentation:
        instrumentation.record_metric("semantic_cache_stored", stored)
        instrumentation.record_metric(
            "semantic_cache_write_duration_ms",
            max((instrumentation.clock() - write_started) * 1000, 0.0),
        )

    return answer, sources, personalization


def _sources_from_supervisor(result: SupervisorResult) -> list[KnowledgeSource]:
    sources: list[KnowledgeSource] = []
    seen: set[str] = set()
    for task_result in result.task_results:
        for evidence in task_result.evidence:
            if evidence.source_type != "knowledge" or evidence.evidence_id in seen:
                continue
            seen.add(evidence.evidence_id)
            metadata = evidence.metadata
            sources.append(
                KnowledgeSource(
                    document_id=str(metadata.get("document_id") or evidence.evidence_id),
                    filename=str(metadata.get("filename") or "Approved knowledge"),
                    category=str(metadata.get("category") or "general"),
                    chunk_index=int(metadata.get("chunk_index") or 0),
                    page_number=(
                        int(metadata["page_number"])
                        if metadata.get("page_number") is not None
                        else None
                    ),
                    text=evidence.content,
                    score=float(metadata.get("score") or 0.0),
                )
            )
    return sources


async def store_streamed_answer_in_cache(
    prepared: PreparedKnowledgeAnswer,
    answer: str,
    instrumentation: AskPerformanceInstrumentation,
) -> bool:
    if prepared.cache_result is None or prepared.cached_answer is not None:
        return False
    started = instrumentation.clock()
    try:
        stored = await semantic_cache.store(
            result=prepared.cache_result,
            answer=answer,
            sources=prepared.sources,
            personalization=prepared.personalization,
            selected_model=prepared.model_override,
            model_role=(
                prepared.model_routing.model_role if prepared.model_routing else None
            ),
            result_type="generated_answer",
        )
    except Exception:
        stored = False
    instrumentation.record_metric("semantic_cache_stored", stored)
    instrumentation.record_metric(
        "semantic_cache_write_duration_ms",
        max((instrumentation.clock() - started) * 1000, 0.0),
    )
    return stored
