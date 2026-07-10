import json
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.schemas.openai import ChatCompletionsRequest
from app.services.ai_router import ai_router
from app.services.ollama_service import OllamaServiceError, ollama_service
from app.services.orchestrator_service import orchestrator_service

router = APIRouter(tags=["OpenAI compatibility"])


def verify_api_key(authorization: str | None) -> None:
    expected = f"Bearer {settings.ctv_ai_api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


@router.get("/models")
async def list_models(
    authorization: str | None = Header(default=None),
) -> dict:
    verify_api_key(authorization)
    created = int(time.time())

    return {
        "object": "list",
        "data": [
            {
                "id": model,
                "object": "model",
                "created": created,
                "owned_by": "ctv-ai",
            }
            for model in ai_router.supported_models()
        ],
    }


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionsRequest,
    authorization: str | None = Header(default=None),
):
    verify_api_key(authorization)

    raw_messages = [message.model_dump() for message in request.messages]
    last_user_message = next(
        (
            item["content"]
            for item in reversed(raw_messages)
            if item["role"] == "user"
        ),
        "",
    )

    if request.model == "ctv-ai-auto":
        route = await orchestrator_service.decide(last_user_message, "auto")
        assistant = route.assistant
        selected_model = route.model
    else:
        assistant = ai_router.assistant_for_model(request.model)
        selected_model = settings.ollama_model

    messages = ai_router.build_messages(raw_messages, assistant)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if request.stream:
        async def event_stream() -> AsyncIterator[str]:
            try:
                async for content in ollama_service.stream_chat(
                    messages,
                    model=selected_model,
                ):
                    chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                final_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except OllamaServiceError as exc:
                error = {"error": {"message": str(exc), "type": "server_error"}}
                yield f"data: {json.dumps(error)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    try:
        content = await ollama_service.chat(
            messages,
            model=selected_model,
        )
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
