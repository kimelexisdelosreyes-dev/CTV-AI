from fastapi import APIRouter, HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_router import ai_router
from app.services.ollama_service import OllamaServiceError

router = APIRouter(tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        answer = await ai_router.chat(
            message=request.message,
            assistant=request.assistant,
        )
        return ChatResponse(
            response=answer,
            assistant=request.assistant,
        )
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
