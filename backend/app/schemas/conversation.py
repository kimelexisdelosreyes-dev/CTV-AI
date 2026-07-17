from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    first_prompt: str | None = Field(default=None, max_length=10000)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ConversationMessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ConversationPublic(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class ConversationMessagePublic(BaseModel):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationPublic]
    limit: int
    offset: int
    has_more: bool


class ConversationDetailResponse(BaseModel):
    conversation: ConversationPublic
    messages: list[ConversationMessagePublic]
    limit: int
    offset: int
    has_more: bool
