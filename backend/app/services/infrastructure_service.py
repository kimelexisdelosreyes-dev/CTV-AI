import httpx
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.embedding_service import embedding_service


async def database_status() -> str:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unavailable"


async def qdrant_status() -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.qdrant_url}/collections")
            response.raise_for_status()
        return "healthy"
    except Exception:
        return "unavailable"


async def embedding_status() -> dict[str, str]:
    return await embedding_service.readiness()
