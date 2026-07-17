from fastapi import APIRouter

from app.services.infrastructure_service import (
    database_status,
    embedding_status,
    qdrant_status,
)

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


@router.get("/status")
async def status() -> dict[str, object]:
    return {
        "postgresql": await database_status(),
        "qdrant": await qdrant_status(),
        "embedding": await embedding_status(),
    }
