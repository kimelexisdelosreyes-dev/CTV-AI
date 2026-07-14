from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.employee import DepartmentCreate, DepartmentPublic
from app.services.employee_service import add_department, list_departments

router = APIRouter(prefix="/admin", tags=["employee-admin"])


def require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(403, "Administrator access required.")


@router.get("/departments", response_model=list[DepartmentPublic])
async def departments(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin(user)
    return await list_departments(db)


@router.post("/departments", response_model=DepartmentPublic)
async def create_department(payload: DepartmentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin(user)
    return await add_department(db, payload)
