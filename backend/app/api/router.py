from fastapi import APIRouter

from app.api.routes import (
    auth,
    chat,
    health,
    infrastructure,
    openai_compat,
    orchestrator,
    version,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(version.router)
api_router.include_router(infrastructure.router)
api_router.include_router(auth.router)
api_router.include_router(orchestrator.router)
api_router.include_router(chat.router)

openai_router = APIRouter()
openai_router.include_router(openai_compat.router)
