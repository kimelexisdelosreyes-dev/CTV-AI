from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.employee import (
    Department, EmployeeMemory, EmployeePreference, EmployeeProfile,
    EmployeeSkill, EmployeeTool, MemoryStatus,
)
from app.db.models.user import User
from app.schemas.employee import (
    DepartmentCreate, EmployeeMemoryCreate, EmployeeMemoryUpdate,
    EmployeePreferenceUpdate, EmployeeProfileUpdate, EmployeeSkillCreate,
    EmployeeToolCreate,
)


async def ensure_profile(db: AsyncSession, user: User) -> EmployeeProfile:
    profile = await db.get(EmployeeProfile, user.id)
    if profile is None:
        profile = EmployeeProfile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def ensure_preferences(db: AsyncSession, user: User) -> EmployeePreference:
    item = await db.get(EmployeePreference, user.id)
    if item is None:
        item = EmployeePreference(user_id=user.id)
        db.add(item)
        await db.commit()
        await db.refresh(item)
    return item


async def save_profile(db: AsyncSession, user: User, payload: EmployeeProfileUpdate):
    item = await ensure_profile(db, user)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def save_preferences(db: AsyncSession, user: User, payload: EmployeePreferenceUpdate):
    item = await ensure_preferences(db, user)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def list_for_user(db: AsyncSession, model, user_id: UUID, order_by):
    result = await db.execute(
        select(model).where(model.user_id == user_id).order_by(order_by)
    )
    return list(result.scalars().all())


async def list_skills(db: AsyncSession, user: User):
    return await list_for_user(db, EmployeeSkill, user.id, EmployeeSkill.name)


async def list_tools(db: AsyncSession, user: User):
    return await list_for_user(db, EmployeeTool, user.id, EmployeeTool.name)


async def list_memories(db: AsyncSession, user: User):
    result = await db.execute(
        select(EmployeeMemory)
        .where(EmployeeMemory.employee_user_id == user.id)
        .order_by(EmployeeMemory.created_at.desc())
    )
    return list(result.scalars().all())


async def add_skill(db: AsyncSession, user: User, payload: EmployeeSkillCreate):
    item = EmployeeSkill(user_id=user.id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def add_tool(db: AsyncSession, user: User, payload: EmployeeToolCreate):
    item = EmployeeTool(user_id=user.id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def add_memory(db: AsyncSession, user: User, payload: EmployeeMemoryCreate):
    confirmed = payload.confirm_immediately
    item = EmployeeMemory(
        employee_user_id=user.id,
        memory_type=payload.memory_type,
        content=payload.content,
        source=payload.source,
        visibility=payload.visibility,
        confidence=payload.confidence,
        status=MemoryStatus.confirmed if confirmed else MemoryStatus.proposed,
        created_by_user_id=user.id,
        reviewed_by_user_id=user.id if confirmed else None,
        reviewed_at=datetime.now(timezone.utc) if confirmed else None,
        expires_at=payload.expires_at,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_memory(db: AsyncSession, user: User, memory_id: UUID, payload: EmployeeMemoryUpdate):
    item = await db.get(EmployeeMemory, memory_id)
    if item is None or item.employee_user_id != user.id:
        raise LookupError("Memory not found.")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(item, key, value)
    if "status" in changes:
        item.reviewed_by_user_id = user.id
        item.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_owned(db: AsyncSession, model, item_id: UUID, user_id: UUID, owner_field: str):
    item = await db.get(model, item_id)
    if item is None or getattr(item, owner_field) != user_id:
        raise LookupError("Item not found.")
    await db.delete(item)
    await db.commit()


async def build_context(db: AsyncSession, user: User) -> str:
    profile = await ensure_profile(db, user)
    preferences = await ensure_preferences(db, user)
    skills = await list_skills(db, user)
    tools = await list_tools(db, user)
    memories = [
        item for item in await list_memories(db, user)
        if item.status == MemoryStatus.confirmed
        and (item.expires_at is None or item.expires_at > datetime.now(timezone.utc))
    ]

    return (
        f"Employee: {user.full_name}\n"
        f"Role: {user.role.value}\n"
        f"Job title: {profile.job_title or 'Not set'}\n"
        f"Experience: {profile.experience_level.value}\n"
        f"Responsibilities: {profile.primary_responsibilities or 'Not set'}\n"
        f"Specialties: {profile.specialties or 'Not set'}\n"
        f"Preferred language: {profile.preferred_language}\n"
        f"Response style: {profile.response_style.value}\n"
        f"Detail level: {profile.detail_level.value}\n"
        f"Prefers checklists: {preferences.prefers_checklists}\n"
        f"Visual examples: {preferences.prefers_visual_examples}\n"
        f"Technical terminology: {preferences.comfortable_with_technical_terms}\n"
        f"Output format: {preferences.preferred_output_format}\n"
        f"Skills: {', '.join(s.name for s in skills) or 'None'}\n"
        f"Tools: {', '.join(t.name for t in tools) or 'None'}\n"
        f"Confirmed memories:\n"
        + ("\n".join(f"- {m.memory_type}: {m.content}" for m in memories) or "- None")
    )


async def list_departments(db: AsyncSession):
    result = await db.execute(
        select(Department).where(Department.is_active.is_(True)).order_by(Department.name)
    )
    return list(result.scalars().all())


async def add_department(db: AsyncSession, payload: DepartmentCreate):
    item = Department(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
