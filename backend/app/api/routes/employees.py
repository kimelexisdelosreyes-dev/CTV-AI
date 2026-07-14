from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.employee import EmployeeMemory, EmployeeSkill, EmployeeTool, MemoryStatus
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.employee import *
from app.services import employee_service as service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/me/profile", response_model=EmployeeProfilePublic)
async def profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.ensure_profile(db, user)


@router.put("/me/profile", response_model=EmployeeProfilePublic)
async def save_profile(payload: EmployeeProfileUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.save_profile(db, user, payload)


@router.get("/me/preferences", response_model=EmployeePreferencePublic)
async def preferences(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.ensure_preferences(db, user)


@router.put("/me/preferences", response_model=EmployeePreferencePublic)
async def save_preferences(payload: EmployeePreferenceUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.save_preferences(db, user, payload)


@router.get("/me/skills", response_model=list[EmployeeSkillPublic])
async def skills(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.list_skills(db, user)


@router.post("/me/skills", response_model=EmployeeSkillPublic)
async def add_skill(payload: EmployeeSkillCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.add_skill(db, user, payload)


@router.delete("/me/skills/{item_id}", status_code=204)
async def delete_skill(item_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        await service.delete_owned(db, EmployeeSkill, item_id, user.id, "user_id")
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)


@router.get("/me/tools", response_model=list[EmployeeToolPublic])
async def tools(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.list_tools(db, user)


@router.post("/me/tools", response_model=EmployeeToolPublic)
async def add_tool(payload: EmployeeToolCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.add_tool(db, user, payload)


@router.delete("/me/tools/{item_id}", status_code=204)
async def delete_tool(item_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        await service.delete_owned(db, EmployeeTool, item_id, user.id, "user_id")
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)


@router.get("/me/memories", response_model=list[EmployeeMemoryPublic])
async def memories(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.list_memories(db, user)


@router.post("/me/memories", response_model=EmployeeMemoryPublic)
async def add_memory(payload: EmployeeMemoryCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await service.add_memory(db, user, payload)


@router.put("/me/memories/{item_id}", response_model=EmployeeMemoryPublic)
async def edit_memory(item_id: UUID, payload: EmployeeMemoryUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        return await service.update_memory(db, user, item_id, payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/me/memories/{item_id}", status_code=204)
async def delete_memory(item_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        await service.delete_owned(db, EmployeeMemory, item_id, user.id, "employee_user_id")
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)


@router.get("/me/context", response_model=EmployeeContextPublic)
async def context(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await service.ensure_profile(db, user)
    preferences = await service.ensure_preferences(db, user)
    skills = await service.list_skills(db, user)
    tools = await service.list_tools(db, user)
    active = [m for m in await service.list_memories(db, user) if m.status == MemoryStatus.confirmed]
    return EmployeeContextPublic(
        profile=profile,
        preferences=preferences,
        skills=skills,
        tools=tools,
        active_memories=active,
        context_text=await service.build_context(db, user),
    )
