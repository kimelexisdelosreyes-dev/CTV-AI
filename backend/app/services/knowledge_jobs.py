import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.models.knowledge_document import KnowledgeDocument
from app.db.session import AsyncSessionLocal
from app.services.document_parser import inspect_document, parse_document
from app.services.embedding_service import embedding_service
from app.services.text_chunker import chunk_sections
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

async def process_document_job(document_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        record = await db.get(KnowledgeDocument, document_id)
        if record is None:
            return

        record.started_at = datetime.now(timezone.utc)
        record.completed_at = None
        record.chunk_count = 0
        record.pages_processed = 0
        record.ocr_pages = 0

        try:
            await vector_store.delete_document(str(record.id))
            path = Path(record.stored_path)
            if not path.exists():
                raise FileNotFoundError("Stored source file no longer exists.")

            record.page_count = inspect_document(path)
            record.status = "processing"
            record.stage = "extracting"
            record.progress_percent = 5
            record.error_message = None
            await db.commit()

            loop = asyncio.get_running_loop()

            def page_progress(processed: int, total: int, used_ocr: bool) -> None:
                record.pages_processed = processed
                if used_ocr:
                    record.ocr_pages += 1
                    record.stage = "ocr"
                else:
                    record.stage = "extracting"
                record.progress_percent = 5 + int((processed / max(total, 1)) * 35)

            sections = await loop.run_in_executor(
                None,
                lambda: parse_document(path, page_progress),
            )
            await db.commit()

            if not sections:
                raise RuntimeError("No readable text could be extracted or OCR-processed.")

            record.stage = "chunking"
            record.progress_percent = 45
            await db.commit()

            chunks = chunk_sections(
                sections,
                chunk_size=settings.knowledge_chunk_size,
                overlap=settings.knowledge_chunk_overlap,
            )
            if not chunks:
                raise RuntimeError("Document produced no searchable chunks.")

            record.chunk_count = len(chunks)
            record.stage = "embedding"
            record.progress_percent = 50
            await db.commit()

            embeddings = []
            embed_batch = settings.knowledge_embed_batch_size

            for start in range(0, len(chunks), embed_batch):
                batch = chunks[start : start + embed_batch]
                embeddings.extend(await embedding_service.embed([item.text for item in batch]))
                record.progress_percent = 50 + int(
                    (min(start + len(batch), len(chunks)) / len(chunks)) * 30
                )
                await db.commit()

            record.stage = "indexing"
            record.progress_percent = 82
            await db.commit()

            qdrant_batch = settings.knowledge_qdrant_batch_size
            for start in range(0, len(chunks), qdrant_batch):
                chunk_batch = chunks[start : start + qdrant_batch]
                vector_batch = embeddings[start : start + qdrant_batch]
                await vector_store.upsert_chunks(
                    str(record.id),
                    record.filename,
                    record.category,
                    chunk_batch,
                    vector_batch,
                )
                record.progress_percent = 82 + int(
                    (min(start + len(chunk_batch), len(chunks)) / len(chunks)) * 17
                )
                await db.commit()

            record.status = "ready"
            record.stage = "ready"
            record.progress_percent = 100
            record.error_message = None
            record.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as exc:
            logger.exception("Knowledge ingestion failed: %s", document_id)
            record.status = "failed"
            record.stage = "failed"
            record.error_message = str(exc)[:4000]
            record.completed_at = datetime.now(timezone.utc)
            await db.commit()
