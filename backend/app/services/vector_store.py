import uuid

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.schemas.knowledge import KnowledgeSource
from app.services.service_errors import CompanyBrainServiceError


class VectorStoreError(CompanyBrainServiceError):
    category = "vector_store_unavailable"
    status_code = 503
    safe_detail = "Knowledge search is temporarily unavailable."

class VectorStore:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(url=settings.qdrant_url)

    async def ensure_collection(self, vector_size: int) -> None:
        if not await self.client.collection_exists(settings.knowledge_collection):
            await self.client.create_collection(
                collection_name=settings.knowledge_collection,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    async def upsert_chunks(
        self,
        document_id: str,
        filename: str,
        category: str,
        chunks: list,
        embeddings: list[list[float]],
    ) -> None:
        if not embeddings:
            return
        await self.ensure_collection(len(embeddings[0]))
        namespace = uuid.UUID(document_id)
        points = [
            models.PointStruct(
                id=str(uuid.uuid5(namespace, f"chunk-{chunk.chunk_index}")),
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "category": category,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                },
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        await self.client.upsert(
            collection_name=settings.knowledge_collection,
            points=points,
            wait=True,
        )

    async def delete_document(self, document_id: str) -> None:
        if not await self.client.collection_exists(settings.knowledge_collection):
            return
        await self.client.delete(
            collection_name=settings.knowledge_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        category: str | None = None,
    ) -> list[KnowledgeSource]:
        if not await self.client.collection_exists(settings.knowledge_collection):
            return []
        query_filter = None
        if category:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="category",
                        match=models.MatchValue(value=category),
                    )
                ]
            )
        try:
            response = await self.client.query_points(
                collection_name=settings.knowledge_collection,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:
            raise VectorStoreError() from exc
        return [
            KnowledgeSource(
                document_id=str((point.payload or {}).get("document_id", "")),
                filename=str((point.payload or {}).get("filename", "Unknown")),
                category=str((point.payload or {}).get("category", "general")),
                chunk_index=int((point.payload or {}).get("chunk_index", 0)),
                page_number=(point.payload or {}).get("page_number"),
                text=str((point.payload or {}).get("text", "")),
                score=float(point.score),
            )
            for point in response.points
        ]

vector_store = VectorStore()
