from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/version")
async def version() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "version": settings.app_version,
    }
