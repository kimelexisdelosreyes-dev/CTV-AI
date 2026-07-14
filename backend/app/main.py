from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router, dashboard_router, openai_router
from app.core.config import settings
from app.core.logging import configure_logging
from fastapi.middleware.cors import CORSMiddleware


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
app.include_router(openai_router, prefix="/v1")
app.include_router(dashboard_router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "knowledge_dashboard": "/admin/knowledge",
    }
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3001",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)