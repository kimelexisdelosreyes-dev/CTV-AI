import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExperienceLevel(str, enum.Enum):
    trainee = "trainee"
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class ResponseStyle(str, enum.Enum):
    concise = "concise"
    step_by_step = "step_by_step"
    detailed = "detailed"
    visual = "visual"
    conversational = "conversational"


class DetailLevel(str, enum.Enum):
    brief = "brief"
    standard = "standard"
    deep = "deep"


class MemoryVisibility(str, enum.Enum):
    private = "private"
    employee = "employee"
    manager = "manager"
    department = "department"
    hr = "hr"
    company = "company"


class MemoryStatus(str, enum.Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    rejected = "rejected"
    archived = "archived"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    experience_level: Mapped[ExperienceLevel] = mapped_column(
        Enum(ExperienceLevel, name="experience_level"),
        default=ExperienceLevel.intermediate,
        nullable=False,
    )
    primary_responsibilities: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    specialties: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    preferred_language: Mapped[str] = mapped_column(
        String(50),
        default="English",
        nullable=False,
    )
    response_style: Mapped[ResponseStyle] = mapped_column(
        Enum(ResponseStyle, name="response_style"),
        default=ResponseStyle.step_by_step,
        nullable=False,
    )
    detail_level: Mapped[DetailLevel] = mapped_column(
        Enum(DetailLevel, name="detail_level"),
        default=DetailLevel.standard,
        nullable=False,
    )
    profile_visibility: Mapped[MemoryVisibility] = mapped_column(
        Enum(MemoryVisibility, name="memory_visibility"),
        default=MemoryVisibility.employee,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EmployeePreference(Base):
    __tablename__ = "employee_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prefers_checklists: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    prefers_visual_examples: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    comfortable_with_technical_terms: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    preferred_output_format: Mapped[str] = mapped_column(
        String(50),
        default="bullets",
        nullable=False,
    )
    requires_approval_for: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    custom_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_employee_skill_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[ExperienceLevel] = mapped_column(
        Enum(ExperienceLevel, name="skill_level"),
        default=ExperienceLevel.intermediate,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class EmployeeTool(Base):
    __tablename__ = "employee_tools"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_employee_tool_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    proficiency: Mapped[ExperienceLevel] = mapped_column(
        Enum(ExperienceLevel, name="tool_proficiency"),
        default=ExperienceLevel.intermediate,
        nullable=False,
    )
    primary_tool: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class EmployeeMemory(Base):
    __tablename__ = "employee_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    employee_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    memory_type: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(100),
        default="employee",
        nullable=False,
    )
    visibility: Mapped[MemoryVisibility] = mapped_column(
        Enum(MemoryVisibility, name="memory_visibility"),
        default=MemoryVisibility.employee,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    status: Mapped[MemoryStatus] = mapped_column(
        Enum(MemoryStatus, name="memory_status"),
        default=MemoryStatus.proposed,
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
