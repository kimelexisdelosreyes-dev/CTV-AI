import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
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
)
from app.services.performance_event_store import performance_event_store
from app.services.performance_instrumentation import AskPerformanceInstrumentation

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
performance_logger = logging.getLogger("ctv_one.performance")


def log_ask_performance(
    instrumentation: AskPerformanceInstrumentation,
    outcome: str,
) -> None:
    fields = instrumentation.to_log_fields(outcome)
    performance_event_store.record(fields)
    performance_logger.info(fields)


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
    sources = await search_knowledge(
        request.query,
        request.top_k,
        selected,
    )

    return KnowledgeSearchResponse(
        query=request.query,
        sources=sources,
    )


@router.post("/ask", response_model=KnowledgeAskResponse)
async def ask(
    request: KnowledgeAskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    instrumentation = AskPerformanceInstrumentation()

    try:
        with instrumentation.measure("total_request"):
            selected = resolved_collection(
                request.collection,
                request.category,
            )

            answer, sources, personalization = await answer_with_knowledge(
                question=request.question,
                top_k=request.top_k,
                category=selected,
                assistant=request.assistant,
                use_employee_context=request.use_employee_context,
                current_user=current_user,
                db=db,
                instrumentation=instrumentation,
            )

            with instrumentation.measure("response_formatting"):
                response = KnowledgeAskResponse(
                    answer=answer,
                    sources=sources,
                    personalization=personalization,
                )
    except Exception as exc:
        instrumentation.mark_failure(exc)
        log_ask_performance(instrumentation, "error")
        raise

    instrumentation.mark_success()
    log_ask_performance(instrumentation, "success")
    return response
