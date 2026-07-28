import asyncio
import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, dashboard_router, openai_router
from app.agents.bootstrap import agent_runtime_manager, builtin_runtime_dependencies
from app.atlas.bootstrap import atlas_runtime_manager
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
    await agent_runtime_manager.initialize(builtin_runtime_dependencies())
    # Atlas owns an empty, idle provider registry in Sprint 3.1. It is started
    # independently after Forge and never participates in request processing.
    await atlas_runtime_manager.initialize()
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
        await atlas_runtime_manager.shutdown()
        await agent_runtime_manager.shutdown()
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


@app.middleware("http")
async def server_timing_middleware(request: Request, call_next):
    started = perf_counter()
    request.state.server_request_started_at = started
    response = await call_next(request)
    total_ms = max((perf_counter() - started) * 1000, 0.0)
    endpoint_ms = float(getattr(request.state, "endpoint_handler_duration_ms", 0.0))
    pre_endpoint_ms = float(getattr(request.state, "pre_endpoint_duration_ms", 0.0))
    serialization_and_middleware_ms = max(total_ms - endpoint_ms - pre_endpoint_ms, 0.0)
    response.headers["X-Server-Duration-Ms"] = f"{total_ms:.3f}"
    response.headers[
        "X-Response-Serialization-And-Middleware-Ms"
    ] = f"{serialization_and_middleware_ms:.3f}"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
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
