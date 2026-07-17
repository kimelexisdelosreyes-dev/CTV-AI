from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.context import ContextMetadata


class KnowledgeCollectionPublic(BaseModel):
    slug: str
    name: str
    description: str
    icon: str
    employee_visible: bool


class KnowledgeDocumentPublic(BaseModel):
    id: UUID
    filename: str
    content_type: str
    category: str
    uploaded_by: str
    status: str
    stage: str
    progress_percent: int
    page_count: int
    pages_processed: int
    ocr_pages: int
    chunk_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    ready_documents: int
    failed_documents: int
    processing_documents: int
    total_chunks: int
    categories: dict[str, int]


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=10000)
    top_k: int = Field(default=5, ge=1, le=20)
    category: str | None = Field(default=None, max_length=100)
    collection: str | None = Field(default=None, max_length=100)


class KnowledgeSource(BaseModel):
    document_id: str
    filename: str
    category: str
    chunk_index: int
    page_number: int | None
    text: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    sources: list[KnowledgeSource]


class KnowledgeAskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=10000)
    top_k: int = Field(default=5, ge=1, le=12)
    category: str | None = Field(default=None, max_length=100)
    collection: str | None = Field(default=None, max_length=100)
    conversation_id: UUID | None = None
    client_message_id: UUID | None = None
    assistant: Literal[
        "general",
        "production",
        "graphics",
        "drone",
        "it",
        "coder",
    ] = "general"
    use_employee_context: bool = True


class KnowledgeAskResponse(BaseModel):
    answer: str
    sources: list[KnowledgeSource]
    personalization: ContextMetadata
    conversation_id: UUID | None = None
