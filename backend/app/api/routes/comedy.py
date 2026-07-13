from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.comedy import ComedyProfilePublic, ComedyProfileUpdate
from app.services.comedy_profile_service import (
    get_profile,
    to_public,
    upsert_profile,
)

router = APIRouter(prefix="/comedy", tags=["comedy"])


@router.get("/profile", response_model=ComedyProfilePublic)
async def read_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComedyProfilePublic:
    profile = await get_profile(db, current_user.email)

    if profile is None:
        return ComedyProfilePublic(
            user_email=current_user.email,
            preferred_language="English",
            humor_level="light",
            likes=[],
            safe_roast_topics=[],
            off_limit_topics=[],
            consent_to_roasting=False,
        )

    return to_public(profile)


@router.put("/profile", response_model=ComedyProfilePublic)
async def update_profile(
    payload: ComedyProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComedyProfilePublic:
    profile = await upsert_profile(db, current_user.email, payload)
    return to_public(profile)
