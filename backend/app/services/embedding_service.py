import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingServiceError(RuntimeError):
    pass

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
            logger.exception("Embedding request failed")
            raise EmbeddingServiceError(
                f"Could not generate embeddings. Confirm '{settings.ollama_embedding_model}' is installed."
            ) from exc
        embeddings = response.json().get("embeddings")
        if not embeddings or len(embeddings) != len(texts):
            raise EmbeddingServiceError("Ollama returned invalid embeddings.")
        return embeddings

embedding_service = EmbeddingService()
