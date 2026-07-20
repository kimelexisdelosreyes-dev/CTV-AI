import logging
import asyncio
import json
from time import perf_counter
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.knowledge_collections import (
    KNOWLEDGE_COLLECTIONS,
    collection_slugs,
    normalize_collection,
)
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.knowledge import (
    KnowledgeAskRequest,
    KnowledgeAskResponse,
    KnowledgeCollectionPublic,
    KnowledgeDocumentPublic,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
)
from app.services.knowledge_service import (
    KnowledgeServiceError,
    answer_with_knowledge,
    delete_document,
    get_document,
    get_stats,
    list_documents,
    queue_document,
    retry_document,
    search_knowledge,
    store_streamed_answer_in_cache,
)
from app.services.inference_queue import (
    InferenceQueueError,
    inference_queue,
    priority_for_model_role,
)
from app.services.model_router import configured_default_model
from app.services import conversation_service
from app.services.performance_event_store import performance_event_store
from app.services.performance_instrumentation import AskPerformanceInstrumentation
from app.services.service_errors import CompanyBrainServiceError
from app.services.conversation_service import ConversationNotFoundError
from app.supervisor.permissions import snapshot_authenticated_user
from app.services.ollama_service import OllamaInferenceTimeoutError, ollama_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
performance_logger = logging.getLogger("ctv_one.performance")
application_logger = logging.getLogger("ctv_one.knowledge")


def log_ask_performance(
    instrumentation: AskPerformanceInstrumentation,
    outcome: str,
) -> None:
    fields = instrumentation.to_log_fields(outcome)
    performance_event_store.record(fields)
    performance_logger.info(fields)


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def service_error_headers(
    exc: CompanyBrainServiceError,
    request_id: str,
) -> dict[str, str]:
    headers = {
        "X-Request-ID": request_id,
        "X-Error-Category": exc.category,
    }
    retry_after = getattr(exc, "retry_after_seconds", None)
    if isinstance(retry_after, int) and retry_after > 0:
        headers["Retry-After"] = str(retry_after)
    return headers


async def append_request_user_message(
    db: AsyncSession,
    user: User,
    request: KnowledgeAskRequest,
) -> None:
    args = (db, user, request.conversation_id, request.question)
    if request.client_message_id is None:
        await conversation_service.append_user_message_for_request(*args)
    else:
        await conversation_service.append_user_message_for_request(
            *args,
            request.client_message_id,
        )


def require_editor(user: User) -> None:
    if user.role not in {UserRole.admin, UserRole.manager}:
        raise HTTPException(
            status_code=403,
            detail="Admin or manager required.",
        )


def resolved_collection(
    collection: str | None,
    category: str | None,
) -> str | None:
    value = normalize_collection(collection or category)

    if value is not None and value not in collection_slugs():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown knowledge collection: {value}",
        )

    return value


@router.get(
    "/collections",
    response_model=list[KnowledgeCollectionPublic],
)
async def collections(
    _: User = Depends(get_current_user),
):
    return [
        KnowledgeCollectionPublic(
            slug=item.slug,
            name=item.name,
            description=item.description,
            icon=item.icon,
            employee_visible=item.employee_visible,
        )
        for item in KNOWLEDGE_COLLECTIONS
    ]


@router.post("/documents", response_model=KnowledgeDocumentPublic)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_editor(current_user)
    selected = resolved_collection(category, None) or "general"

    try:
        return await queue_document(
            file,
            selected,
            current_user.email,
            db,
        )
    except KnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/documents", response_model=list[KnowledgeDocumentPublic])
async def documents(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_documents(db)


@router.get(
    "/documents/{document_id}",
    response_model=KnowledgeDocumentPublic,
)
async def document(
    document_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_document(document_id, db)
    except KnowledgeServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/documents/{document_id}/retry",
    response_model=KnowledgeDocumentPublic,
)
async def retry(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_editor(current_user)

    try:
        return await retry_document(document_id, db)
    except KnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def stats(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_stats(db)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_editor(current_user)

    try:
        await delete_document(document_id, db)
    except KnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(status_code=204)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search(
    request: KnowledgeSearchRequest,
    _: User = Depends(get_current_user),
):
    selected = resolved_collection(
        request.collection,
        request.category,
    )
    try:
        sources = await search_knowledge(
            request.query,
            request.top_k,
            selected,
        )
    except CompanyBrainServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_detail,
            headers={"X-Error-Category": exc.category},
        ) from exc

    return KnowledgeSearchResponse(
        query=request.query,
        sources=sources,
    )


@router.post("/ask", response_model=KnowledgeAskResponse)
async def ask(
    request: KnowledgeAskRequest,
    http_response: Response,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    instrumentation = AskPerformanceInstrumentation()
    endpoint_started = perf_counter()
    pre_endpoint_ms = max(
        (
            endpoint_started
            - getattr(http_request.state, "server_request_started_at", endpoint_started)
        )
        * 1000,
        0.0,
    )
    http_request.state.pre_endpoint_duration_ms = pre_endpoint_ms
    authentication_ms = float(
        getattr(http_request.state, "authentication_duration_ms", 0.0)
    )
    instrumentation.record_metric(
        "request_validation_duration_ms",
        max(pre_endpoint_ms - authentication_ms, 0.0),
    )
    instrumentation.record_metric(
        "authentication_duration_ms",
        getattr(http_request.state, "authentication_duration_ms", 0.0),
    )
    instrumentation.record_metric(
        "authentication_decode_duration_ms",
        getattr(http_request.state, "authentication_decode_duration_ms", 0.0),
    )
    instrumentation.record_metric(
        "authentication_query_duration_ms",
        getattr(http_request.state, "authentication_query_duration_ms", 0.0),
    )
    authenticated_user = snapshot_authenticated_user(current_user)
    user_message_saved = False

    try:
        with instrumentation.measure("total_request"):
            selected = resolved_collection(
                request.collection,
                request.category,
            )

            if request.conversation_id is not None:
                try:
                    await append_request_user_message(db, authenticated_user, request)
                except ConversationNotFoundError as exc:
                    raise HTTPException(
                        status_code=404,
                        detail="Conversation not found.",
                    ) from exc
                user_message_saved = True

            answer, sources, personalization = await answer_with_knowledge(
                question=request.question,
                top_k=request.top_k,
                category=selected,
                assistant=request.assistant,
                use_employee_context=request.use_employee_context,
                current_user=authenticated_user,
                db=db,
                instrumentation=instrumentation,
                conversation_id=request.conversation_id,
                supervisor_mode=request.supervisor_mode,
            )

            with instrumentation.measure("response_formatting"):
                result = KnowledgeAskResponse(
                    answer=answer,
                    sources=sources,
                    personalization=personalization,
                    conversation_id=request.conversation_id,
                )
            if request.conversation_id is not None:
                with instrumentation.measure("persistence"):
                    await conversation_service.append_assistant_message_for_request(
                        db,
                        authenticated_user,
                        request.conversation_id,
                        answer,
                    )
    except CompanyBrainServiceError as exc:
        if request.conversation_id is not None and user_message_saved:
            await conversation_service.append_assistant_message_for_request(
                db,
                authenticated_user,
                request.conversation_id,
                exc.safe_detail,
            )
        instrumentation.mark_failure(exc)
        log_ask_performance(instrumentation, "error")
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_detail,
            headers=service_error_headers(exc, instrumentation.request_id),
        ) from exc
    except Exception as exc:
        instrumentation.mark_failure(exc)
        log_ask_performance(instrumentation, "error")
        application_logger.exception(
            "Unexpected Company Brain error request_id=%s category=ai_request_error",
            instrumentation.request_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Company Brain could not complete this request.",
            headers={
                "X-Request-ID": instrumentation.request_id,
                "X-Error-Category": "ai_request_error",
            },
        ) from exc

    endpoint_handler_ms = max((perf_counter() - endpoint_started) * 1000, 0.0)
    http_request.state.endpoint_handler_duration_ms = endpoint_handler_ms
    instrumentation.record_metric("endpoint_handler_duration_ms", endpoint_handler_ms)
    instrumentation.record_metric(
        "response_model_construction_duration_ms",
        instrumentation.durations_ms.get("response_formatting", 0.0),
    )
    instrumentation.record_metric(
        "persistence_duration_ms",
        instrumentation.durations_ms.get("persistence", 0.0),
    )
    instrumentation.mark_success()
    log_ask_performance(instrumentation, "success")
    http_response.headers["X-Request-ID"] = instrumentation.request_id
    http_response.headers["X-Result-Type"] = (
        "cached_answer"
        if instrumentation.metrics.get("semantic_cache_hit")
        else
        "no_knowledge_fallback"
        if not sources and not personalization.operational_context_applied
        else "generated_answer"
    )
    for metric_name, header_name in (
        ("inference_queue_wait_ms", "X-Inference-Queue-Wait-Ms"),
        ("inference_queue_priority", "X-Inference-Priority"),
        ("inference_queue_depth_at_entry", "X-Inference-Queue-Depth"),
        ("model_selected", "X-Inference-Model"),
    ):
        value = instrumentation.metrics.get(metric_name)
        if value is not None:
            http_response.headers[header_name] = str(value)
    return result


@router.post("/ask/stream")
async def ask_stream(
    request: KnowledgeAskRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream visible assistant text only; prompts and retrieved context stay server-side."""
    authenticated_user = snapshot_authenticated_user(current_user)

    async def event_stream():
        instrumentation = AskPerformanceInstrumentation()
        instrumentation.record_metric(
            "authentication_duration_ms",
            getattr(http_request.state, "authentication_duration_ms", 0.0),
        )
        user_message_saved = False
        answer_parts: list[str] = []
        token_chunk_count = 0
        stream_started = perf_counter()

        yield sse_event(
            "start",
            {
                "request_id": instrumentation.request_id,
                "conversation_id": str(request.conversation_id)
                if request.conversation_id
                else None,
            },
        )

        try:
            with instrumentation.measure("total_request"):
                selected = resolved_collection(request.collection, request.category)
                if request.conversation_id is not None:
                    try:
                        await append_request_user_message(db, authenticated_user, request)
                    except ConversationNotFoundError as exc:
                        raise CompanyBrainServiceError(
                            category="conversation_not_found",
                            status_code=404,
                            safe_detail="Conversation not found.",
                        ) from exc
                    user_message_saved = True

                supervisor_events: asyncio.Queue[tuple[str, dict[str, object]]] = (
                    asyncio.Queue()
                )

                async def supervisor_event(
                    event_name: str,
                    event_data: dict[str, object],
                ) -> None:
                    await supervisor_events.put((event_name, event_data))

                prepare_task = asyncio.create_task(
                    answer_with_knowledge(
                        question=request.question,
                        top_k=request.top_k,
                        category=selected,
                        assistant=request.assistant,
                        use_employee_context=request.use_employee_context,
                        current_user=authenticated_user,
                        db=db,
                        instrumentation=instrumentation,
                        conversation_id=request.conversation_id,
                        prepare_for_stream=True,
                        supervisor_mode=request.supervisor_mode,
                        supervisor_event_callback=supervisor_event,
                    )
                )
                event_task: asyncio.Task | None = None
                try:
                    while not prepare_task.done():
                        if await http_request.is_disconnected():
                            prepare_task.cancel()
                            await asyncio.gather(prepare_task, return_exceptions=True)
                            raise asyncio.CancelledError()
                        event_task = asyncio.create_task(supervisor_events.get())
                        completed, _ = await asyncio.wait(
                            {prepare_task, event_task},
                            timeout=0.1,
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if event_task in completed:
                            event_name, event_data = event_task.result()
                            yield sse_event(event_name, event_data)
                        else:
                            event_task.cancel()
                            await asyncio.gather(event_task, return_exceptions=True)
                    prepared = await prepare_task
                    while not supervisor_events.empty():
                        event_name, event_data = supervisor_events.get_nowait()
                        yield sse_event(event_name, event_data)
                finally:
                    if event_task is not None and not event_task.done():
                        event_task.cancel()
                        await asyncio.gather(event_task, return_exceptions=True)
                    if not prepare_task.done():
                        prepare_task.cancel()
                        await asyncio.gather(prepare_task, return_exceptions=True)

                instrumentation.record_stream_started()
                selected_model = prepared.model_override or configured_default_model()
                model_role = (
                    prepared.model_routing.model_role
                    if prepared.model_routing is not None
                    else "default"
                )
                context_ready_data = {
                    "selected_context_types": instrumentation.metrics.get(
                        "required_context_components", []
                    ),
                    "retrieval_total_duration_ms": instrumentation.metrics.get(
                        "retrieval_total_duration_ms", 0.0
                    ),
                    "semantic_cache_hit": instrumentation.metrics.get(
                        "semantic_cache_hit", False
                    ),
                    "semantic_cache_hit_type": instrumentation.metrics.get(
                        "semantic_cache_hit_type", "none"
                    ),
                    "model_name": selected_model,
                    "model_role": model_role,
                    "priority": priority_for_model_role(model_role),
                }

                if prepared.cached_answer is not None:
                    instrumentation.record_context_ready()
                    yield sse_event("context_ready", context_ready_data)
                    answer_parts.append(prepared.cached_answer)
                    token_chunk_count += 1
                    instrumentation.record_first_stream_token()
                    yield sse_event("token", {"text": prepared.cached_answer})
                elif prepared.fallback_answer is not None:
                    instrumentation.record_context_ready()
                    yield sse_event("context_ready", context_ready_data)
                    answer_parts.append(prepared.fallback_answer)
                    yield sse_event("token", {"text": prepared.fallback_answer})
                elif prepared.supervised_answer is not None:
                    instrumentation.record_context_ready()
                    yield sse_event("context_ready", context_ready_data)
                    answer_parts.append(prepared.supervised_answer)
                    token_chunk_count += 1
                    instrumentation.record_first_stream_token()
                    yield sse_event("token", {"text": prepared.supervised_answer})
                else:
                    if isinstance(db, AsyncSession) and db.in_transaction():
                        await db.rollback()
                    admission = await inference_queue.submit(
                        request_id=instrumentation.request_id,
                        user_id=str(authenticated_user.id),
                        conversation_id=(
                            str(request.conversation_id)
                            if request.conversation_id
                            else None
                        ),
                        model_name=selected_model,
                        model_role=model_role,
                        streaming=True,
                        estimated_cost_class=model_role,
                    )
                    inference_queue.record_result(
                        instrumentation,
                        admission.initial_result,
                    )
                    if admission.initial_result.queued:
                        yield sse_event(
                            "queue_status",
                            {
                                "queued": True,
                                "queue_position": admission.initial_result.queue_position,
                                "estimated_wait_seconds": (
                                    admission.initial_result.estimated_wait_seconds
                                ),
                                "priority": admission.initial_result.priority,
                                "model_role": model_role,
                            },
                        )
                    try:
                        lease = await admission.wait(
                            cancellation_check=http_request.is_disconnected
                        )
                    except InferenceQueueError as exc:
                        if exc.result is not None:
                            inference_queue.record_result(
                                instrumentation,
                                exc.result,
                            )
                        raise
                    inference_queue.record_lease(instrumentation, lease)
                    instrumentation.record_context_ready()
                    yield sse_event("context_ready", context_ready_data)
                    lease_cancelled = False
                    try:
                        with instrumentation.measure("ollama_total"):
                            instrumentation.model_name = selected_model
                            instrumentation.record_inference_start()
                            try:
                                async with asyncio.timeout(
                                    inference_queue.config.default_timeout_seconds
                                ):
                                    async for chunk in ollama_service.stream_chat(
                                        prepared.messages,
                                        model=selected_model,
                                    ):
                                        if await http_request.is_disconnected():
                                            lease_cancelled = True
                                            instrumentation.record_stream_completion(
                                                token_chunk_count=token_chunk_count,
                                                answer="".join(answer_parts),
                                                cancelled=True,
                                            )
                                            instrumentation.mark_failure(
                                                asyncio.CancelledError()
                                            )
                                            log_ask_performance(
                                                instrumentation,
                                                "cancelled",
                                            )
                                            return
                                        if chunk.text:
                                            answer_parts.append(chunk.text)
                                            token_chunk_count += 1
                                            instrumentation.record_first_stream_token()
                                            yield sse_event(
                                                "token",
                                                {"text": chunk.text},
                                            )
                                        if chunk.done and chunk.metadata:
                                            instrumentation.record_ollama_metrics(
                                                chunk.metadata
                                            )
                            except TimeoutError as exc:
                                instrumentation.record_metric(
                                    "inference_timed_out",
                                    True,
                                )
                                raise OllamaInferenceTimeoutError() from exc
                    except asyncio.CancelledError:
                        lease_cancelled = True
                        instrumentation.record_metric("inference_cancelled", True)
                        raise
                    finally:
                        lease_duration_ms = await lease.release(
                            cancelled=lease_cancelled
                        )
                        instrumentation.record_metric(
                            "inference_lease_duration_ms",
                            lease_duration_ms,
                        )

                answer = "".join(answer_parts)
                if not answer.strip():
                    raise CompanyBrainServiceError(
                        category="model_inference_empty_response",
                        status_code=503,
                        safe_detail="Model inference returned an empty response.",
                    )
                instrumentation.record_answer(answer)
                await store_streamed_answer_in_cache(
                    prepared,
                    answer,
                    instrumentation,
                )
                assistant_persisted = False
                if request.conversation_id is not None:
                    await conversation_service.append_assistant_message_for_request(
                        db,
                        authenticated_user,
                        request.conversation_id,
                        answer,
                    )
                    assistant_persisted = True
                instrumentation.record_stream_completion(
                    token_chunk_count=token_chunk_count,
                    answer=answer,
                    assistant_persisted=assistant_persisted,
                )
                instrumentation.mark_success()
                log_ask_performance(instrumentation, "success")
                yield sse_event(
                    "done",
                    {
                        "answer_chars": len(answer),
                        "first_token_latency_ms": instrumentation.metrics.get(
                            "first_token_latency_ms"
                        ),
                        "duration_ms": round((perf_counter() - stream_started) * 1000, 3),
                        "inference_queue_wait_ms": instrumentation.metrics.get(
                            "inference_queue_wait_ms", 0.0
                        ),
                    },
                )
        except asyncio.CancelledError:
            instrumentation.record_stream_completion(
                token_chunk_count=token_chunk_count,
                answer="".join(answer_parts),
                cancelled=True,
            )
            instrumentation.mark_failure(asyncio.CancelledError())
            log_ask_performance(instrumentation, "cancelled")
            raise
        except CompanyBrainServiceError as exc:
            instrumentation.record_stream_completion(
                token_chunk_count=token_chunk_count,
                answer="".join(answer_parts),
                error_category=exc.category,
            )
            instrumentation.mark_failure(exc)
            log_ask_performance(instrumentation, "error")
            yield sse_event(
                "error",
                {"error_category": exc.category, "safe_detail": exc.safe_detail},
            )
        except Exception as exc:
            application_logger.exception(
                "Unexpected Company Brain stream error request_id=%s category=ai_request_error",
                instrumentation.request_id,
            )
            error = CompanyBrainServiceError(
                category="ai_request_error",
                status_code=500,
                safe_detail="Company Brain could not complete this request.",
            )
            instrumentation.record_stream_completion(
                token_chunk_count=token_chunk_count,
                answer="".join(answer_parts),
                error_category=error.category,
            )
            instrumentation.mark_failure(error)
            log_ask_performance(instrumentation, "error")
            yield sse_event(
                "error",
                {"error_category": error.category, "safe_detail": error.safe_detail},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
