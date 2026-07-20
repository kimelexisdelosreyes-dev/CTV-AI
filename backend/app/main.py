import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, dashboard_router, openai_router
from app.connectors.bootstrap import register_builtin_connectors
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.embedding_service import embedding_service
from app.services.inference_queue import inference_queue
from app.services.operations_snapshot_service import operations_sync_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    register_builtin_connectors()
    await inference_queue.start()
    readiness = await embedding_service.readiness()
    if readiness.get("status") != "healthy":
        logging.getLogger(__name__).warning(
            "embedding.readiness category=%s model=%s",
            readiness.get("category"),
            readiness.get("model"),
        )
    sync_stop = asyncio.Event()
    sync_task = None
    if settings.ctv_one_monday_snapshot_refresh_enabled:
        sync_task = asyncio.create_task(operations_sync_loop(sync_stop))
    try:
        yield
    finally:
        await inference_queue.shutdown()
        sync_stop.set()
        if sync_task is not None:
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Private, local-first AI platform for multimedia production.",
    lifespan=lifespan,
)

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
