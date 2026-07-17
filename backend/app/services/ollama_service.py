import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.services.service_errors import CompanyBrainServiceError

logger = logging.getLogger(__name__)


class OllamaServiceError(CompanyBrainServiceError):
    category = "model_inference_unavailable"
    status_code = 503
    safe_detail = "Model inference is temporarily unavailable."


class OllamaInferenceTimeoutError(OllamaServiceError):
    category = "model_inference_timeout"
    status_code = 504
    safe_detail = "Model inference timed out."


class OllamaMalformedResponseError(OllamaServiceError):
    category = "model_inference_malformed_response"
    safe_detail = "Model inference returned an invalid response."


class OllamaEmptyResponseError(OllamaServiceError):
    category = "model_inference_empty_response"
    safe_detail = "Model inference returned an empty response."


class OllamaTruncatedResponseError(OllamaServiceError):
    category = "model_inference_truncated"
    status_code = 503
    safe_detail = "Model inference stopped before producing a usable answer."


class OllamaUpstreamError(OllamaServiceError):
    category = "model_inference_upstream_error"
    safe_detail = "Model inference returned an upstream error."


def response_diagnostics(
    *,
    response: httpx.Response | None,
    data: dict[str, Any] | None,
    json_ok: bool,
    model: str,
) -> dict[str, object]:
    message = data.get("message") if isinstance(data, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    thinking = message.get("thinking") if isinstance(message, dict) else None
    response_field = data.get("response") if isinstance(data, dict) else None

    return {
        "http_status": response.status_code if response is not None else None,
        "content_type": response.headers.get("content-type")
        if response is not None
        else None,
        "json_ok": json_ok,
        "raw_response_chars": len(response.text) if response is not None else None,
        "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else [],
        "message_present": isinstance(message, dict),
        "message_type": type(message).__name__,
        "message_keys": sorted(message.keys()) if isinstance(message, dict) else [],
        "message_content_present": content is not None,
        "message_content_type": type(content).__name__,
        "message_content_chars": len(content) if isinstance(content, str) else None,
        "message_thinking_present": thinking is not None,
        "message_thinking_type": type(thinking).__name__,
        "message_thinking_chars": len(thinking) if isinstance(thinking, str) else None,
        "response_field_present": response_field is not None,
        "response_field_type": type(response_field).__name__,
        "response_field_chars": (
            len(response_field) if isinstance(response_field, str) else None
        ),
        "done": data.get("done") if isinstance(data, dict) else None,
        "done_reason": data.get("done_reason") if isinstance(data, dict) else None,
        "model": model,
        "prompt_eval_count": data.get("prompt_eval_count")
        if isinstance(data, dict)
        else None,
        "eval_count": data.get("eval_count") if isinstance(data, dict) else None,
        "total_duration": data.get("total_duration") if isinstance(data, dict) else None,
        "load_duration": data.get("load_duration") if isinstance(data, dict) else None,
        "prompt_eval_duration": data.get("prompt_eval_duration")
        if isinstance(data, dict)
        else None,
        "eval_duration": data.get("eval_duration") if isinstance(data, dict) else None,
        "has_error": "error" in data if isinstance(data, dict) else None,
    }


def extract_chat_content(
    data: dict[str, Any],
    diagnostics: dict[str, object],
) -> str:
    if data.get("error"):
        raise OllamaUpstreamError(diagnostics=diagnostics)

    message = data.get("message")
    if not isinstance(message, dict):
        raise OllamaMalformedResponseError(diagnostics=diagnostics)

    if data.get("done") is False:
        raise OllamaMalformedResponseError(diagnostics=diagnostics)

    done_reason = str(data.get("done_reason") or "").lower()
    if done_reason in {"length", "num_predict"}:
        raise OllamaTruncatedResponseError(diagnostics=diagnostics)

    content = message.get("content")
    if not isinstance(content, str):
        raise OllamaMalformedResponseError(diagnostics=diagnostics)

    if content.strip():
        return content

    thinking = message.get("thinking")
    if isinstance(thinking, str) and thinking.strip():
        raise OllamaTruncatedResponseError(diagnostics=diagnostics)

    raise OllamaEmptyResponseError(diagnostics=diagnostics)


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
            "think": settings.ollama_think,
        }
        if settings.ollama_num_predict > 0:
            payload["options"] = {"num_predict": settings.ollama_num_predict}

        try:
            async with httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=settings.request_timeout_seconds,
            ) as client:
                response = await client.post("/api/chat", json=payload)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    diagnostics = response_diagnostics(
                        response=response,
                        data=None,
                        json_ok=False,
                        model=str(payload["model"]),
                    )
                    raise OllamaUpstreamError(diagnostics=diagnostics) from exc
        except httpx.TimeoutException as exc:
            logger.warning("ollama.chat_timeout model=%s", payload["model"])
            raise OllamaInferenceTimeoutError() from exc
        except OllamaServiceError:
            raise
        except httpx.HTTPError as exc:
            logger.warning("ollama.chat_failed model=%s", payload["model"])
            raise OllamaServiceError() from exc

        try:
            data = response.json()
        except ValueError as exc:
            diagnostics = response_diagnostics(
                response=response,
                data=None,
                json_ok=False,
                model=str(payload["model"]),
            )
            raise OllamaMalformedResponseError(diagnostics=diagnostics) from exc

        diagnostics = response_diagnostics(
            response=response,
            data=data,
            json_ok=True,
            model=str(payload["model"]),
        )
        content = extract_chat_content(data, diagnostics)

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
