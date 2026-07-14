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
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.knowledge import (
    KnowledgeAskRequest,
    KnowledgeAskResponse,
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

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def require_editor(user: User) -> None:
    if user.role not in {UserRole.admin, UserRole.manager}:
        raise HTTPException(
            status_code=403,
            detail="Admin or manager required.",
        )


@router.post("/documents", response_model=KnowledgeDocumentPublic)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_editor(current_user)

    try:
        return await queue_document(
            file,
            category,
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
    sources = await search_knowledge(
        request.query,
        request.top_k,
        request.category,
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
    answer, sources, personalization = await answer_with_knowledge(
        question=request.question,
        top_k=request.top_k,
        category=request.category,
        assistant=request.assistant,
        use_employee_context=request.use_employee_context,
        current_user=current_user,
        db=db,
    )

    return KnowledgeAskResponse(
        answer=answer,
        sources=sources,
        personalization=personalization,
    )
