from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import (
    Conversation,
    ConversationMessage,
    ConversationMessageRole,
)
from app.db.models.user import User

MAX_TITLE_CHARS = 64
MAX_MESSAGE_CHARS = 20_000
SAFE_MODEL_ERROR_MESSAGE = (
    "Company Brain could not generate a usable answer for this request."
)


class ConversationNotFoundError(RuntimeError):
    pass


class ConversationMessageConflictError(RuntimeError):
    pass


def title_from_prompt(prompt: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (prompt or "").strip())
    if not cleaned:
        return "New conversation"
    if len(cleaned) <= MAX_TITLE_CHARS:
        return cleaned
    return cleaned[: MAX_TITLE_CHARS - 3].rstrip() + "..."


def safe_message_content(content: str) -> str:
    cleaned = content.strip()
    if len(cleaned) <= MAX_MESSAGE_CHARS:
        return cleaned
    return cleaned[:MAX_MESSAGE_CHARS].rstrip()


async def create_conversation(
    db: AsyncSession,
    user: User,
    *,
    title: str | None = None,
    first_prompt: str | None = None,
) -> Conversation:
    conversation = Conversation(
        user_id=user.id,
        title=safe_title(title) if title else title_from_prompt(first_prompt),
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(
    db: AsyncSession,
    user: User,
    *,
    limit: int,
    offset: int,
    include_archived: bool = False,
) -> tuple[list[Conversation], bool]:
    statement = select(Conversation).where(Conversation.user_id == user.id)
    if not include_archived:
        statement = statement.where(Conversation.archived_at.is_(None))

    statement = (
        statement.order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    result = await db.execute(statement)
    conversations = list(result.scalars().all())
    return conversations[:limit], len(conversations) > limit


async def get_owned_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise ConversationNotFoundError("Conversation not found.")
    return conversation


async def read_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[Conversation, list[ConversationMessage], bool]:
    conversation = await get_owned_conversation(db, user, conversation_id)
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(
            ConversationMessage.created_at.asc(),
            ConversationMessage.id.asc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )
    messages = list(result.scalars().all())
    return conversation, messages[:limit], len(messages) > limit


async def recent_messages(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    *,
    limit: int,
) -> list[ConversationMessage]:
    conversation = await get_owned_conversation(db, user, conversation_id)
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(
            ConversationMessage.created_at.desc(),
            ConversationMessage.id.desc(),
        )
        .limit(limit)
    )
    messages = list(result.scalars().all())
    return list(reversed(messages))


async def rename_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    title: str,
) -> Conversation:
    conversation = await get_owned_conversation(db, user, conversation_id)
    conversation.title = safe_title(title)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def archive_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
) -> Conversation:
    conversation = await get_owned_conversation(db, user, conversation_id)
    conversation.archived_at = datetime.now(timezone.utc)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def delete_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
) -> None:
    await get_owned_conversation(db, user, conversation_id)
    await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
    await db.commit()


async def append_message(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    *,
    role: ConversationMessageRole,
    content: str,
    message_id: uuid.UUID | None = None,
) -> ConversationMessage:
    conversation = await get_owned_conversation(db, user, conversation_id)
    if message_id is not None:
        existing = await db.get(ConversationMessage, message_id)
        if existing is not None:
            if (
                existing.conversation_id == conversation.id
                and existing.role == role
                and existing.content == safe_message_content(content)
            ):
                return existing
            raise ConversationMessageConflictError("Client message ID is already in use.")
    message = ConversationMessage(
        id=message_id,
        conversation_id=conversation.id,
        role=role,
        content=safe_message_content(content),
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def append_visible_exchange(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    *,
    user_prompt: str,
    assistant_content: str,
) -> None:
    conversation = await get_owned_conversation(db, user, conversation_id)
    conversation.updated_at = datetime.now(timezone.utc)
    db.add_all(
        [
            ConversationMessage(
                conversation_id=conversation.id,
                role=ConversationMessageRole.user,
                content=safe_message_content(user_prompt),
            ),
            ConversationMessage(
                conversation_id=conversation.id,
                role=ConversationMessageRole.assistant,
                content=safe_message_content(assistant_content),
            ),
        ]
    )
    await db.commit()


async def append_user_message_for_request(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    user_prompt: str,
    client_message_id: uuid.UUID | None = None,
) -> None:
    await append_message(
        db,
        user,
        conversation_id,
        role=ConversationMessageRole.user,
        content=user_prompt,
        message_id=client_message_id,
    )


async def append_assistant_message_for_request(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    assistant_content: str,
) -> None:
    await append_message(
        db,
        user,
        conversation_id,
        role=ConversationMessageRole.assistant,
        content=assistant_content,
    )


async def message_count(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
    )
    return int(result.scalar_one())


def safe_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title.strip())
    return cleaned[:MAX_TITLE_CHARS] or "New conversation"
