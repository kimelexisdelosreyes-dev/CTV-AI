import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaServiceError(RuntimeError):
    pass


class OllamaService:
    async def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": settings.ollama_model,
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
                "CTV-AI could not reach Ollama. Confirm that Ollama is running "
                f"at {settings.ollama_base_url} and that model "
                f"'{settings.ollama_model}' is installed."
            ) from exc

        data = response.json()
        content = data.get("message", {}).get("content")

        if not content:
            raise OllamaServiceError("Ollama returned an empty or invalid response.")

        return content


ollama_service = OllamaService()
