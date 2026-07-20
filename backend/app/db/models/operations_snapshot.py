import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, func, text as sql_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OperationsSnapshot(Base):
    __tablename__ = "operations_snapshots"
    __table_args__ = (
        Index(
            "uq_operations_snapshots_one_active",
            "status",
            unique=True,
            postgresql_where=sql_text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(40), default="monday", nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_category: Mapped[str | None] = mapped_column(String(80))
    safe_error: Mapped[str | None] = mapped_column(String(300))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    source_revision: Mapped[str | None] = mapped_column(String(200))
    task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    board_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refresh_duration_ms: Mapped[float | None] = mapped_column(Float)
    triggered_by: Mapped[str | None] = mapped_column(String(320))
    trigger_type: Mapped[str | None] = mapped_column(String(30))
    previous_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operations_snapshots.id", ondelete="SET NULL")
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_changed: Mapped[bool | None] = mapped_column(Boolean)
    semantic_cache_invalidated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    cache_invalidation_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tasks: Mapped[list["OperationTask"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", lazy="selectin"
    )


class OperationTask(Base):
    __tablename__ = "operation_tasks"
    __table_args__ = (
        Index("ix_operation_tasks_snapshot_external", "snapshot_id", "external_id", unique=True),
        Index("ix_operation_tasks_snapshot_status", "snapshot_id", "status"),
        Index("ix_operation_tasks_snapshot_due", "snapshot_id", "due_at"),
        Index("ix_operation_tasks_snapshot_priority", "snapshot_id", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operations_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    board_id: Mapped[str | None] = mapped_column(String(120))
    board_name: Mapped[str | None] = mapped_column(String(300))
    group_id: Mapped[str | None] = mapped_column(String(120))
    group_name: Mapped[str | None] = mapped_column(String(300))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str | None] = mapped_column(String(200), index=True)
    priority: Mapped[str | None] = mapped_column(String(200), index=True)
    assignee_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    owner_key: Mapped[str | None] = mapped_column(String(500), index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    updated_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    snapshot: Mapped[OperationsSnapshot] = relationship(back_populates="tasks")
