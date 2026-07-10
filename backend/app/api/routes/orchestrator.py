from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.model_registry import MODEL_REGISTRY
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.orchestrator import (
    OrchestratedChatRequest,
    OrchestratedChatResponse,
    RouteDecision,
    RouteRequest,
)
from app.services.ollama_service import OllamaServiceError
from app.services.orchestrator_service import orchestrator_service

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.get("/models")
async def models(
    _: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    return [
        {
            "key": profile.key,
            "ollama_model": profile.ollama_model,
            "capabilities": list(profile.capabilities),
            "description": profile.description,
        }
        for profile in MODEL_REGISTRY.values()
    ]


@router.post("/route", response_model=RouteDecision)
async def route(
    request: RouteRequest,
    _: User = Depends(get_current_user),
) -> RouteDecision:
    try:
        return await orchestrator_service.decide(
            request.message,
            request.assistant,
        )
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/chat", response_model=OrchestratedChatResponse)
async def chat(
    request: OrchestratedChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrchestratedChatResponse:
    try:
        response, route_decision = await orchestrator_service.chat(
            message=request.message,
            conversation=request.conversation,
            override=request.assistant,
            user_email=current_user.email,
            db=db,
        )
        return OrchestratedChatResponse(
            response=response,
            route=route_decision,
        )
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
