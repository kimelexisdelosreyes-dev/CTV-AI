import uuid
from collections import Counter
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import ASSISTANT_PROMPTS
from app.db.models.knowledge_document import KnowledgeDocument
from app.schemas.knowledge import KnowledgeSource, KnowledgeStatsResponse
from app.services.document_parser import SUPPORTED_EXTENSIONS, parse_document
from app.services.embedding_service import embedding_service
from app.services.ollama_service import ollama_service
from app.services.text_chunker import chunk_sections
from app.services.vector_store import vector_store


class KnowledgeServiceError(RuntimeError):
    pass


async def save_and_index_document(
    upload: UploadFile,
    category: str,
    uploaded_by: str,
    db: AsyncSession,
) -> KnowledgeDocument:
    original_name = Path(upload.filename or "document").name
    extension = Path(original_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise KnowledgeServiceError(f"Unsupported file type. Supported: {supported}")

    content = await upload.read()
    if not content:
        raise KnowledgeServiceError("The uploaded document is empty.")

    max_bytes = settings.knowledge_max_file_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise KnowledgeServiceError(
            f"File exceeds the {settings.knowledge_max_file_mb} MB limit."
        )

    document_id = uuid.uuid4()
    upload_dir = Path(settings.knowledge_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{document_id}{extension}"
    stored_path.write_bytes(content)

    record = KnowledgeDocument(
        id=document_id,
        filename=original_name,
        stored_path=str(stored_path),
        content_type=upload.content_type or "application/octet-stream",
        category=category.strip().lower() or "general",
        uploaded_by=uploaded_by,
        status="processing",
        chunk_count=0,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    try:
        sections = parse_document(stored_path)
        if not sections:
            raise KnowledgeServiceError(
                "No readable text was extracted. Scanned PDFs require OCR."
            )

        chunks = chunk_sections(
            sections,
            chunk_size=settings.knowledge_chunk_size,
            overlap=settings.knowledge_chunk_overlap,
        )
        embeddings = await embedding_service.embed([chunk.text for chunk in chunks])

        await vector_store.upsert_chunks(
            document_id=str(record.id),
            filename=record.filename,
            category=record.category,
            chunks=chunks,
            embeddings=embeddings,
        )

        record.status = "ready"
        record.chunk_count = len(chunks)
        record.error_message = None
    except Exception as exc:
        record.status = "failed"
        record.error_message = str(exc)[:2000]
        await db.commit()
        raise
    else:
        await db.commit()
        await db.refresh(record)
        return record


async def list_documents(db: AsyncSession) -> list[KnowledgeDocument]:
    result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    )
    return list(result.scalars().all())


async def get_stats(db: AsyncSession) -> KnowledgeStatsResponse:
    documents = await list_documents(db)
    categories = Counter(document.category for document in documents)

    return KnowledgeStatsResponse(
        total_documents=len(documents),
        ready_documents=sum(document.status == "ready" for document in documents),
        failed_documents=sum(document.status == "failed" for document in documents),
        processing_documents=sum(
            document.status == "processing" for document in documents
        ),
        total_chunks=sum(document.chunk_count for document in documents),
        categories=dict(sorted(categories.items())),
    )


async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    record = await db.get(KnowledgeDocument, document_id)
    if record is None:
        raise KnowledgeServiceError("Knowledge document not found.")

    await vector_store.delete_document(str(record.id))

    path = Path(record.stored_path)
    if path.exists() and path.is_file():
        path.unlink()

    await db.delete(record)
    await db.commit()


async def search_knowledge(
    query: str,
    top_k: int,
    category: str | None,
) -> list[KnowledgeSource]:
    embedding = (await embedding_service.embed([query]))[0]
    return await vector_store.search(embedding, top_k, category)


async def answer_with_knowledge(
    question: str,
    top_k: int,
    category: str | None,
    assistant: str,
) -> tuple[str, list[KnowledgeSource]]:
    sources = await search_knowledge(question, top_k, category)

    if not sources:
        return (
            "I could not find relevant approved company knowledge for that question.",
            [],
        )

    context_blocks = []
    for index, source in enumerate(sources, start=1):
        page = f", page {source.page_number}" if source.page_number else ""
        context_blocks.append(
            f"[Source {index}] {source.filename}{page}\n{source.text}"
        )

    system_prompt = ASSISTANT_PROMPTS.get(
        assistant,
        ASSISTANT_PROMPTS["general"],
    ).strip()

    messages = [
        {
            "role": "system",
            "content": (
                f"{system_prompt}\n\n"
                "Answer only from the approved company context. "
                "If the context is insufficient, say so. Cite sources as "
                "[Source 1], [Source 2], and so on. Do not invent company facts."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                "Approved company context:\n\n"
                + "\n\n".join(context_blocks)
            ),
        },
    ]

    answer = await ollama_service.chat(messages)
    return answer, sources
