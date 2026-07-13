from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.schemas.knowledge import KnowledgeSource


class VectorStore:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(url=settings.qdrant_url)

    async def ensure_collection(self, vector_size: int) -> None:
        exists = await self.client.collection_exists(settings.knowledge_collection)

        if not exists:
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

        points = [
            models.PointStruct(
                id=f"{document_id}-{chunk.chunk_index}",
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
        exists = await self.client.collection_exists(settings.knowledge_collection)
        if not exists:
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
        exists = await self.client.collection_exists(settings.knowledge_collection)
        if not exists:
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

        response = await self.client.query_points(
            collection_name=settings.knowledge_collection,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        results: list[KnowledgeSource] = []
        for point in response.points:
            payload = point.payload or {}
            results.append(
                KnowledgeSource(
                    document_id=str(payload.get("document_id", "")),
                    filename=str(payload.get("filename", "Unknown")),
                    category=str(payload.get("category", "general")),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    page_number=payload.get("page_number"),
                    text=str(payload.get("text", "")),
                    score=float(point.score),
                )
            )

        return results


vector_store = VectorStore()
