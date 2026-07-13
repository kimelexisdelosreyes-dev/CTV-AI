from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ComedyProfile(Base):
    __tablename__ = "comedy_profiles"

    user_email: Mapped[str] = mapped_column(String(320), primary_key=True)
    preferred_language: Mapped[str] = mapped_column(
        String(50),
        default="English",
        nullable=False,
    )
    humor_level: Mapped[str] = mapped_column(
        String(50),
        default="light",
        nullable=False,
    )
    likes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    safe_roast_topics_json: Mapped[str] = mapped_column(
        Text,
        default="[]",
        nullable=False,
    )
    off_limit_topics_json: Mapped[str] = mapped_column(
        Text,
        default="[]",
        nullable=False,
    )
    consent_to_roasting: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
