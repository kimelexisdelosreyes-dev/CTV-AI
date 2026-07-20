from __future__ import annotations

import hashlib
import json
import math
import re
from collections import OrderedDict
from dataclasses import dataclass
from dataclasses import replace as dataclass_replace
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.context_requirements import ContextRequirements
from app.db.models.knowledge_document import KnowledgeDocument
from app.db.models.operations_snapshot import OperationsSnapshot
from app.db.models.semantic_cache import SemanticCacheEntry
from app.db.session import AsyncSessionLocal
from app.schemas.context import ContextMetadata
from app.schemas.knowledge import KnowledgeSource
from app.services.embedding_service import embedding_service


CacheScope = Literal["global_company", "user", "conversation"]

BYPASS_PHRASES = {
    "refresh", "latest", "recalculate", "check again", "ignore cache",
    "regenerate", "update this",
}
CREATIVE_OR_REWRITE_PHRASES = {
    "write a", "rewrite", "reword", "wording", "tone", "make it sound",
    "brainstorm", "creative", "draft a", "compose a",
}
COMPLEX_PHRASES = {
    "analyze", "analysis", "recommend", "recommendation", "strategy",
    "strategic", "forecast", "tradeoff", "pros and cons", "scenario",
}


@dataclass(frozen=True)
class SemanticCacheLookup:
    eligible: bool
    normalized_query: str
    exact_key: str
    scope_key: str
    scope_type: CacheScope
    invalidation_fingerprint: str
    context_route: str
    context_types: tuple[str, ...]
    operations_fingerprint: str | None = None
    knowledge_fingerprint: str | None = None
    skip_reason: str | None = None
    query_embedding: list[float] | None = None


@dataclass(frozen=True)
class SemanticCacheResult:
    hit: bool = False
    hit_type: Literal["exact", "semantic", "none"] = "none"
    answer: str | None = None
    sources: tuple[KnowledgeSource, ...] = ()
    personalization: ContextMetadata | None = None
    similarity_score: float | None = None
    cache_entry_id: UUID | None = None
    age_seconds: float | None = None
    selected_model: str | None = None
    model_role: str | None = None
    skip_reason: str | None = None
    lookup: SemanticCacheLookup | None = None
    lookup_duration_ms: float = 0.0
    cache_source: Literal["hot", "database", "none"] = "none"
    database_query_ms: float = 0.0
    deserialization_ms: float = 0.0
    persistence_ms: float = 0.0


@dataclass(frozen=True)
class _HotExactEntry:
    result: SemanticCacheResult
    created_at: datetime
    expires_at: datetime


def normalize_query(question: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", question.casefold()))


def _digest(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _contains(normalized: str, phrases: set[str]) -> bool:
    padded = f" {normalized} "
    return any(f" {phrase} " in padded for phrase in phrases)


def _context_types(requirements: ContextRequirements) -> tuple[str, ...]:
    return tuple(
        name
        for name, included in (
            ("knowledge", requirements.include_knowledge),
            ("operations", requirements.include_operations),
            ("employee", requirements.include_employee),
            ("history", requirements.include_history),
        )
        if included
    )


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


class SemanticCacheService:
    def __init__(self) -> None:
        self._hot_exact: OrderedDict[str, _HotExactEntry] = OrderedDict()
        self._hot_hit_count = 0

    def _hot_get(
        self, lookup: SemanticCacheLookup, now: datetime, started: float
    ) -> SemanticCacheResult | None:
        item = self._hot_exact.get(lookup.exact_key)
        if item is None:
            return None
        if item.expires_at <= now:
            self._hot_exact.pop(lookup.exact_key, None)
            return None
        self._hot_exact.move_to_end(lookup.exact_key)
        self._hot_hit_count += 1
        return dataclass_replace(
            item.result,
            lookup=lookup,
            age_seconds=max((now - item.created_at).total_seconds(), 0.0),
            lookup_duration_ms=(perf_counter() - started) * 1000,
            cache_source="hot",
            database_query_ms=0.0,
            deserialization_ms=0.0,
            persistence_ms=0.0,
        )

    def _hot_put(
        self,
        exact_key: str,
        result: SemanticCacheResult,
        *,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        maximum = max(settings.ctv_one_semantic_cache_hot_exact_max_entries, 0)
        if maximum == 0:
            return
        self._hot_exact[exact_key] = _HotExactEntry(
            result=result,
            created_at=created_at,
            expires_at=expires_at,
        )
        self._hot_exact.move_to_end(exact_key)
        while len(self._hot_exact) > maximum:
            self._hot_exact.popitem(last=False)

    def clear_hot_exact(self) -> None:
        self._hot_exact.clear()

    async def _state_fingerprints(
        self, context_types: tuple[str, ...]
    ) -> tuple[str | None, str | None]:
        operations_fingerprint = None
        knowledge_fingerprint = None
        async with AsyncSessionLocal() as db:
            if "operations" in context_types:
                snapshot = await db.execute(
                    select(OperationsSnapshot.content_hash)
                    .where(OperationsSnapshot.status == "active")
                    .order_by(OperationsSnapshot.activated_at.desc())
                    .limit(1)
                )
                row = snapshot.first()
                operations_fingerprint = row[0] if row and row[0] else None
            if "knowledge" in context_types:
                revision = await db.execute(
                    select(
                        func.count(KnowledgeDocument.id),
                        func.max(KnowledgeDocument.updated_at),
                        func.sum(KnowledgeDocument.chunk_count),
                    ).where(KnowledgeDocument.status == "ready")
                )
                row = revision.one()
                knowledge_fingerprint = _digest(tuple(row))
        return operations_fingerprint, knowledge_fingerprint

    async def build_lookup(
        self,
        *,
        question: str,
        route_intent: str,
        requirements: ContextRequirements,
        current_user_id: UUID,
        conversation_id: UUID | None,
        assistant: str,
        category: str | None,
    ) -> SemanticCacheLookup:
        normalized = normalize_query(question)
        context_types = _context_types(requirements)
        skip_reason = None
        scope_type: CacheScope = "global_company"
        scope_key = "global_company"

        if not settings.ctv_one_semantic_cache_enabled:
            skip_reason = "disabled"
        elif conversation_id is not None or "history" in context_types:
            scope_type = "conversation"
            scope_key = f"conversation:{conversation_id}"
            skip_reason = "conversation_context"
        elif "employee" in context_types:
            scope_type = "user"
            scope_key = f"user:{current_user_id}"
            skip_reason = "employee_context"
        elif _contains(normalized, BYPASS_PHRASES):
            skip_reason = "bypass_phrase"
        elif _contains(normalized, CREATIVE_OR_REWRITE_PHRASES):
            skip_reason = "creative_or_rewrite"
        elif _contains(normalized, COMPLEX_PHRASES):
            skip_reason = "complex_reasoning"
        elif not ({"knowledge", "operations"} & set(context_types)):
            skip_reason = "unsupported_context"

        operations_fp = knowledge_fp = None
        if skip_reason is None:
            operations_fp, knowledge_fp = await self._state_fingerprints(context_types)
            if "operations" in context_types and operations_fp is None:
                skip_reason = "operations_fingerprint_unavailable"
            if "knowledge" in context_types and knowledge_fp is None:
                skip_reason = "knowledge_fingerprint_unavailable"

        state = {
            "route": route_intent,
            "context_types": context_types,
            "operations": operations_fp,
            "knowledge": knowledge_fp,
            "router_policy": settings.ctv_one_semantic_cache_router_policy_version,
            "prompt_policy": settings.ctv_one_semantic_cache_prompt_policy_version,
            "assistant": assistant,
            "category": category,
            "models": {
                "fast": settings.ctv_one_model_fast,
                "balanced": settings.ctv_one_model_balanced,
                "reasoning": settings.ctv_one_model_reasoning,
                "operations": settings.ctv_one_model_operations,
                "knowledge": settings.ctv_one_model_knowledge,
                "default": settings.ctv_one_model_default,
            },
        }
        invalidation = _digest(state)
        exact_key = _digest(
            {"query": normalized, "scope": scope_key, "state": invalidation}
        )
        return SemanticCacheLookup(
            eligible=skip_reason is None,
            normalized_query=normalized,
            exact_key=exact_key,
            scope_key=scope_key,
            scope_type=scope_type,
            invalidation_fingerprint=invalidation,
            context_route=route_intent,
            context_types=context_types,
            operations_fingerprint=operations_fp,
            knowledge_fingerprint=knowledge_fp,
            skip_reason=skip_reason,
        )

    async def lookup(self, lookup: SemanticCacheLookup) -> SemanticCacheResult:
        started = perf_counter()
        if not lookup.eligible:
            return SemanticCacheResult(
                skip_reason=lookup.skip_reason,
                lookup=lookup,
                lookup_duration_ms=(perf_counter() - started) * 1000,
            )
        now = datetime.now(timezone.utc)
        hot_result = self._hot_get(lookup, now, started)
        if hot_result is not None:
            return hot_result
        async with AsyncSessionLocal() as db:
            entry = None
            hit_type: Literal["exact", "semantic", "none"] = "none"
            similarity = None
            query_embedding = None
            database_query_ms = 0.0
            if settings.ctv_one_semantic_cache_exact_enabled:
                query_started = perf_counter()
                entry = await db.scalar(
                    select(SemanticCacheEntry).where(
                        SemanticCacheEntry.exact_key == lookup.exact_key,
                        SemanticCacheEntry.expires_at > now,
                    )
                )
                database_query_ms += (perf_counter() - query_started) * 1000
                if entry is not None:
                    hit_type = "exact"
            if (
                entry is None
                and settings.ctv_one_semantic_cache_similarity_enabled
            ):
                embeddings = await embedding_service.embed([lookup.normalized_query])
                query_embedding = embeddings[0]
                query_started = perf_counter()
                candidates = (
                    await db.scalars(
                        select(SemanticCacheEntry)
                        .where(
                            SemanticCacheEntry.scope_key == lookup.scope_key,
                            SemanticCacheEntry.invalidation_fingerprint
                            == lookup.invalidation_fingerprint,
                            SemanticCacheEntry.context_route == lookup.context_route,
                            SemanticCacheEntry.expires_at > now,
                            SemanticCacheEntry.question_embedding.is_not(None),
                        )
                        .order_by(SemanticCacheEntry.last_hit_at.desc().nullslast())
                        .limit(settings.ctv_one_semantic_cache_max_candidates)
                    )
                ).all()
                database_query_ms += (perf_counter() - query_started) * 1000
                scored = [
                    (_cosine(query_embedding, candidate.question_embedding), candidate)
                    for candidate in candidates
                    if candidate.question_embedding
                ]
                if scored:
                    similarity, candidate = max(scored, key=lambda item: item[0])
                    if similarity >= settings.ctv_one_semantic_cache_similarity_threshold:
                        entry = candidate
                        hit_type = "semantic"
            if entry is None:
                enriched = SemanticCacheLookup(
                    **{**lookup.__dict__, "query_embedding": query_embedding}
                )
                return SemanticCacheResult(
                    lookup=enriched,
                    similarity_score=similarity,
                    lookup_duration_ms=(perf_counter() - started) * 1000,
                    cache_source="database",
                    database_query_ms=database_query_ms,
                )
            deserialize_started = perf_counter()
            result = SemanticCacheResult(
                hit=True,
                hit_type=hit_type,
                answer=entry.safe_answer,
                sources=tuple(KnowledgeSource.model_validate(item) for item in entry.safe_sources),
                personalization=ContextMetadata.model_validate(entry.personalization),
                similarity_score=similarity,
                cache_entry_id=entry.id,
                age_seconds=max((now - entry.created_at).total_seconds(), 0.0),
                selected_model=entry.model_name,
                model_role=entry.model_role,
                lookup=lookup,
                lookup_duration_ms=(perf_counter() - started) * 1000,
                cache_source="database",
                database_query_ms=database_query_ms,
                deserialization_ms=(perf_counter() - deserialize_started) * 1000,
            )
            self._hot_put(
                lookup.exact_key,
                result,
                created_at=entry.created_at,
                expires_at=entry.expires_at,
            )
            return dataclass_replace(
                result,
                lookup_duration_ms=(perf_counter() - started) * 1000,
            )

    async def store(
        self,
        *,
        result: SemanticCacheResult,
        answer: str,
        sources: list[KnowledgeSource],
        personalization: ContextMetadata,
        selected_model: str | None,
        model_role: str | None,
        result_type: str,
    ) -> bool:
        lookup = result.lookup
        if (
            lookup is None
            or not lookup.eligible
            or not answer.strip()
            or len(answer) > settings.ctv_one_semantic_cache_max_answer_chars
            or personalization.context_degraded
            or result_type not in {"generated_answer"}
        ):
            return False
        embedding = lookup.query_embedding
        if embedding is None and settings.ctv_one_semantic_cache_similarity_enabled:
            embedding = (await embedding_service.embed([lookup.normalized_query]))[0]
        ttl = (
            settings.ctv_one_semantic_cache_operations_ttl_seconds
            if "operations" in lookup.context_types
            else settings.ctv_one_semantic_cache_default_ttl_seconds
        )
        now = datetime.now(timezone.utc)
        safe_sources = [
            {
                "document_id": source.document_id,
                "filename": source.filename,
                "category": source.category,
                "chunk_index": source.chunk_index,
                "page_number": source.page_number,
                "text": "",
                "score": source.score,
            }
            for source in sources
        ]
        values = {
            "normalized_question": lookup.normalized_query,
            "exact_key": lookup.exact_key,
            "question_embedding": embedding,
            "safe_answer": answer,
            "safe_sources": safe_sources,
            "personalization": personalization.model_dump(mode="json"),
            "context_route": lookup.context_route,
            "context_types": list(lookup.context_types),
            "scope_type": lookup.scope_type,
            "scope_key": lookup.scope_key,
            "invalidation_fingerprint": lookup.invalidation_fingerprint,
            "operations_fingerprint": lookup.operations_fingerprint,
            "knowledge_fingerprint": lookup.knowledge_fingerprint,
            "employee_fingerprint": None,
            "conversation_fingerprint": None,
            "model_role": model_role,
            "model_name": selected_model,
            "result_type": result_type,
            "policy_version": settings.ctv_one_semantic_cache_prompt_policy_version,
            "created_at": now,
            "expires_at": now + timedelta(seconds=max(ttl, 1)),
            "last_hit_at": None,
            "hit_count": 0,
        }
        async with AsyncSessionLocal() as db:
            statement = insert(SemanticCacheEntry).values(**values)
            statement = statement.on_conflict_do_update(
                constraint="uq_semantic_cache_exact_key",
                set_={key: value for key, value in values.items() if key != "exact_key"},
            )
            await db.execute(statement)
            await db.commit()
        self._hot_exact.pop(lookup.exact_key, None)
        return True

    async def purge_expired(self) -> int:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(SemanticCacheEntry).where(
                    SemanticCacheEntry.expires_at <= datetime.now(timezone.utc)
                )
            )
            await db.commit()
            self.clear_hot_exact()
            return result.rowcount or 0

    async def invalidate_knowledge(self) -> int:
        return await self._invalidate(SemanticCacheEntry.knowledge_fingerprint.is_not(None))

    async def invalidate_operations(self, fingerprint: str | None = None) -> int:
        condition = SemanticCacheEntry.operations_fingerprint.is_not(None)
        if fingerprint is not None:
            condition = SemanticCacheEntry.operations_fingerprint == fingerprint
        return await self._invalidate(condition)

    async def invalidate_user(self, user_id: UUID) -> int:
        return await self._invalidate(SemanticCacheEntry.scope_key == f"user:{user_id}")

    async def _invalidate(self, condition) -> int:
        async with AsyncSessionLocal() as db:
            result = await db.execute(delete(SemanticCacheEntry).where(condition))
            await db.commit()
            self.clear_hot_exact()
            return result.rowcount or 0

    async def statistics(self) -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            total = await db.scalar(select(func.count(SemanticCacheEntry.id))) or 0
            expired = await db.scalar(
                select(func.count(SemanticCacheEntry.id)).where(
                    SemanticCacheEntry.expires_at <= now
                )
            ) or 0
            hits = await db.scalar(select(func.sum(SemanticCacheEntry.hit_count))) or 0
            return {
                "entry_count": total,
                "expired_count": expired,
                "hit_count": hits + self._hot_hit_count,
            }


semantic_cache = SemanticCacheService()
