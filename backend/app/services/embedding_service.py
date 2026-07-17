import logging
import httpx

from app.core.config import settings
from app.services.service_errors import CompanyBrainServiceError

logger = logging.getLogger(__name__)


class EmbeddingServiceError(CompanyBrainServiceError):
    category = "embedding_unavailable"
    status_code = 503
    safe_detail = "Knowledge retrieval is temporarily unavailable."


class EmbeddingModelMissingError(EmbeddingServiceError):
    category = "embedding_model_missing"
    safe_detail = "The configured embedding model is not available."


class EmbeddingEndpointUnsupportedError(EmbeddingServiceError):
    category = "embedding_endpoint_unsupported"
    safe_detail = "The configured embedding endpoint is not supported."


class EmbeddingTimeoutError(EmbeddingServiceError):
    category = "embedding_timeout"
    status_code = 504
    safe_detail = "Knowledge retrieval timed out."


class EmbeddingMalformedResponseError(EmbeddingServiceError):
    category = "embedding_malformed_response"
    safe_detail = "The embedding service returned an invalid response."


def _embedding_error_from_http(exc: httpx.HTTPError) -> EmbeddingServiceError:
    if isinstance(exc, httpx.TimeoutException):
        return EmbeddingTimeoutError()
    if isinstance(exc, httpx.ConnectError):
        return EmbeddingServiceError()
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 404:
            return EmbeddingModelMissingError()
        return EmbeddingServiceError()
    return EmbeddingServiceError()


class EmbeddingService:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": settings.ollama_embedding_model, "input": texts}
        try:
            async with httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=settings.request_timeout_seconds,
            ) as client:
                response = await client.post("/api/embed", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            error = _embedding_error_from_http(exc)
            logger.warning(
                "embedding.request_failed category=%s model=%s",
                error.category,
                settings.ollama_embedding_model,
            )
            raise error from exc

        try:
            embeddings = response.json().get("embeddings")
        except ValueError as exc:
            raise EmbeddingMalformedResponseError() from exc

        if not embeddings or len(embeddings) != len(texts):
            raise EmbeddingMalformedResponseError()
        return embeddings

    async def readiness(self) -> dict[str, str]:
        try:
            async with httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=settings.embedding_validation_timeout_seconds,
            ) as client:
                tags_response = await client.get("/api/tags")
                tags_response.raise_for_status()
                models = {
                    item.get("name", "")
                    for item in tags_response.json().get("models", [])
                    if item.get("name")
                }
                if settings.ollama_embedding_model not in models:
                    return {
                        "status": "unavailable",
                        "category": EmbeddingModelMissingError.category,
                        "model": settings.ollama_embedding_model,
                    }

                embed_response = await client.post(
                    "/api/embed",
                    json={
                        "model": settings.ollama_embedding_model,
                        "input": ["readiness probe"],
                    },
                )
                embed_response.raise_for_status()
        except httpx.TimeoutException:
            return {
                "status": "unavailable",
                "category": EmbeddingTimeoutError.category,
                "model": settings.ollama_embedding_model,
            }
        except httpx.ConnectError:
            return {
                "status": "unavailable",
                "category": EmbeddingServiceError.category,
                "model": settings.ollama_embedding_model,
            }
        except httpx.HTTPStatusError as exc:
            category = (
                EmbeddingEndpointUnsupportedError.category
                if exc.response.status_code == 404
                else EmbeddingServiceError.category
            )
            return {
                "status": "unavailable",
                "category": category,
                "model": settings.ollama_embedding_model,
            }
        except (ValueError, KeyError):
            return {
                "status": "unavailable",
                "category": EmbeddingMalformedResponseError.category,
                "model": settings.ollama_embedding_model,
            }

        try:
            embeddings = embed_response.json().get("embeddings")
        except ValueError:
            return {
                "status": "unavailable",
                "category": EmbeddingMalformedResponseError.category,
                "model": settings.ollama_embedding_model,
            }

        if not embeddings:
            return {
                "status": "unavailable",
                "category": EmbeddingMalformedResponseError.category,
                "model": settings.ollama_embedding_model,
            }

        return {
            "status": "healthy",
            "category": "ready",
            "model": settings.ollama_embedding_model,
        }

embedding_service = EmbeddingService()
