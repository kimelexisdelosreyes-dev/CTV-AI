from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.db.models.employee import (
    DetailLevel, ExperienceLevel, MemoryStatus, MemoryVisibility, ResponseStyle,
)


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class DepartmentPublic(DepartmentCreate):
    id: UUID
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class EmployeeProfileUpdate(BaseModel):
    department_id: UUID | None = None
    manager_user_id: UUID | None = None
    job_title: str | None = Field(default=None, max_length=200)
    experience_level: ExperienceLevel = ExperienceLevel.intermediate
    primary_responsibilities: str | None = Field(default=None, max_length=5000)
    specialties: str | None = Field(default=None, max_length=5000)
    preferred_language: str = Field(default="English", max_length=50)
    response_style: ResponseStyle = ResponseStyle.step_by_step
    detail_level: DetailLevel = DetailLevel.standard
    profile_visibility: MemoryVisibility = MemoryVisibility.employee


class EmployeeProfilePublic(EmployeeProfileUpdate):
    user_id: UUID
    updated_at: datetime
    model_config = {"from_attributes": True}


class EmployeePreferenceUpdate(BaseModel):
    prefers_checklists: bool = True
    prefers_visual_examples: bool = False
    comfortable_with_technical_terms: bool = True
    preferred_output_format: str = Field(default="bullets", max_length=50)
    requires_approval_for: str | None = Field(default=None, max_length=5000)
    custom_instructions: str | None = Field(default=None, max_length=5000)


class EmployeePreferencePublic(EmployeePreferenceUpdate):
    user_id: UUID
    updated_at: datetime
    model_config = {"from_attributes": True}


class EmployeeSkillCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    level: ExperienceLevel = ExperienceLevel.intermediate
    notes: str | None = Field(default=None, max_length=2000)


class EmployeeSkillPublic(EmployeeSkillCreate):
    id: UUID
    user_id: UUID
    verified: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class EmployeeToolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    proficiency: ExperienceLevel = ExperienceLevel.intermediate
    primary_tool: bool = False
    notes: str | None = Field(default=None, max_length=2000)


class EmployeeToolPublic(EmployeeToolCreate):
    id: UUID
    user_id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class EmployeeMemoryCreate(BaseModel):
    memory_type: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2, max_length=10000)
    source: str = Field(default="employee", max_length=100)
    visibility: MemoryVisibility = MemoryVisibility.employee
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    confirm_immediately: bool = True
    expires_at: datetime | None = None


class EmployeeMemoryUpdate(BaseModel):
    memory_type: str | None = Field(default=None, min_length=2, max_length=100)
    content: str | None = Field(default=None, min_length=2, max_length=10000)
    visibility: MemoryVisibility | None = None
    status: MemoryStatus | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    expires_at: datetime | None = None


class EmployeeMemoryPublic(BaseModel):
    id: UUID
    employee_user_id: UUID
    memory_type: str
    content: str
    source: str
    visibility: MemoryVisibility
    confidence: float
    status: MemoryStatus
    created_by_user_id: UUID
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class EmployeeContextPublic(BaseModel):
    profile: EmployeeProfilePublic
    preferences: EmployeePreferencePublic
    skills: list[EmployeeSkillPublic]
    tools: list[EmployeeToolPublic]
    active_memories: list[EmployeeMemoryPublic]
    context_text: str
