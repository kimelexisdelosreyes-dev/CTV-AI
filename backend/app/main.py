from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Private, local-first AI platform for multimedia production.",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }
