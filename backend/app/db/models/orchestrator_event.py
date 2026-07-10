import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OrchestratorEvent(Base):
    __tablename__ = "orchestrator_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_email: Mapped[str] = mapped_column(String(320), index=True)
    message_preview: Mapped[str] = mapped_column(Text)
    selected_assistant: Mapped[str] = mapped_column(String(50), index=True)
    selected_model: Mapped[str] = mapped_column(String(200))
    confidence: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
