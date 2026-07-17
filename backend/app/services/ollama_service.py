import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaServiceError(RuntimeError):
    pass


class OllamaService:
    async def list_models(self) -> set[str]:
        try:
            async with httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=15.0,
            ) as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Could not list Ollama models")
            raise OllamaServiceError(
                "CTV-AI could not retrieve the installed Ollama models."
            ) from exc

        data = response.json()
        return {
            item.get("name", "")
            for item in data.get("models", [])
            if item.get("name")
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        return_metadata: bool = False,
    ) -> str | tuple[str, dict[str, object]]:
        payload = {
            "model": model or settings.ollama_model,
            "messages": messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=settings.request_timeout_seconds,
            ) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Ollama request failed")
            raise OllamaServiceError(
                "CTV-AI could not reach Ollama or the selected model."
            ) from exc

        data = response.json()
        content = data.get("message", {}).get("content")

        if not content:
            raise OllamaServiceError("Ollama returned an empty or invalid response.")

        if return_metadata:
            return content, data

        return content

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or settings.ollama_model,
            "messages": messages,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=settings.request_timeout_seconds,
            ) as client:
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")

                        if content:
                            yield content
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            logger.exception("Ollama streaming request failed")
            raise OllamaServiceError(
                "CTV-AI lost its connection to Ollama while streaming."
            ) from exc


ollama_service = OllamaService()
