import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.conversation import ConversationMessageRole
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessageCreate,
    ConversationMessagePublic,
    ConversationPublic,
    ConversationRename,
)
from app.services import conversation_service
from app.services.conversation_service import ConversationNotFoundError

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationPublic, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await conversation_service.create_conversation(
        db,
        current_user,
        title=payload.title,
        first_prompt=payload.first_prompt,
    )


@router.get("", response_model=ConversationListResponse)
async def recent(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    include_archived: bool = False,
):
    conversations, has_more = await conversation_service.list_conversations(
        db,
        current_user,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )
    return ConversationListResponse(
        conversations=conversations,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def read(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    try:
        conversation, messages, has_more = await conversation_service.read_conversation(
            db,
            current_user,
            conversation_id,
            limit=limit,
            offset=offset,
        )
    except ConversationNotFoundError as exc:
        raise not_found() from exc

    return ConversationDetailResponse(
        conversation=conversation,
        messages=messages,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.patch("/{conversation_id}", response_model=ConversationPublic)
async def rename(
    conversation_id: uuid.UUID,
    payload: ConversationRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await conversation_service.rename_conversation(
            db,
            current_user,
            conversation_id,
            payload.title,
        )
    except ConversationNotFoundError as exc:
        raise not_found() from exc


@router.post("/{conversation_id}/archive", response_model=ConversationPublic)
async def archive(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await conversation_service.archive_conversation(
            db,
            current_user,
            conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise not_found() from exc


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await conversation_service.delete_conversation(
            db,
            current_user,
            conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise not_found() from exc


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessagePublic,
    status_code=status.HTTP_201_CREATED,
)
async def append_message(
    conversation_id: uuid.UUID,
    payload: ConversationMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await conversation_service.append_message(
            db,
            current_user,
            conversation_id,
            role=ConversationMessageRole(payload.role),
            content=payload.content,
        )
    except ConversationNotFoundError as exc:
        raise not_found() from exc


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Conversation not found.")
