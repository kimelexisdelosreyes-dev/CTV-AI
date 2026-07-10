from fastapi import APIRouter

from app.api.routes import chat, health, openai_compat, version

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(version.router)
api_router.include_router(chat.router)

openai_router = APIRouter()
openai_router.include_router(openai_compat.router)
