import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SemanticCacheEntry(Base):
    __tablename__ = "semantic_cache_entries"
    __table_args__ = (
        UniqueConstraint("exact_key", name="uq_semantic_cache_exact_key"),
        Index("ix_semantic_cache_scope_expiry", "scope_key", "expires_at"),
        Index(
            "ix_semantic_cache_context_state",
            "scope_key",
            "invalidation_fingerprint",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    normalized_question: Mapped[str] = mapped_column(Text, nullable=False)
    exact_key: Mapped[str] = mapped_column(String(64), nullable=False)
    question_embedding: Mapped[list[float] | None] = mapped_column(JSON)
    safe_answer: Mapped[str] = mapped_column(Text, nullable=False)
    safe_sources: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    personalization: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    context_route: Mapped[str] = mapped_column(String(80), nullable=False)
    context_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(160), nullable=False)
    invalidation_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    operations_fingerprint: Mapped[str | None] = mapped_column(String(64))
    knowledge_fingerprint: Mapped[str | None] = mapped_column(String(64))
    employee_fingerprint: Mapped[str | None] = mapped_column(String(64))
    conversation_fingerprint: Mapped[str | None] = mapped_column(String(64))
    model_role: Mapped[str | None] = mapped_column(String(40))
    model_name: Mapped[str | None] = mapped_column(String(160))
    result_type: Mapped[str] = mapped_column(String(40), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_similarity: Mapped[float | None] = mapped_column(Float)
