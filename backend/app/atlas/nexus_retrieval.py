from __future__ import annotations

from enum import StrEnum
from threading import Lock
from time import perf_counter
from typing import Literal

from pydantic import Field, model_validator

from app.atlas.canonical import AtlasCanonicalModel, fingerprint
from app.atlas.providers.nexus import (
    NEXUS_GRAPH_VERSION,
    NexusEntity,
    NexusGraphResult,
    NexusGraphSnapshot,
    NexusRelationship,
    normalize_nexus_identifier,
)


NEXUS_RETRIEVAL_ENGINE_VERSION = "1.0"


class NexusRetrievalMode(StrEnum):
    BALANCED = "balanced"
    ENTITY_FOCUSED = "entity_focused"
    RELATIONSHIP_FOCUSED = "relationship_focused"


RELATIONSHIP_PRIORITY_WEIGHTS: dict[str, int] = {
    "direct_reference": 100,
    "document_in_collection": 90,
    "document_relates_to_project": 85,
    "project_association": 80,
    "asset_related_to": 75,
    "person_reference": 70,
    "media_relation": 65,
    "supports": 50,
    "adapts": 45,
}


ENTITY_PRIORITY_WEIGHTS: dict[str, int] = {
    "policy": 100,
    "knowledge_document": 90,
    "project": 80,
    "media_asset": 70,
    "organization": 65,
    "event": 60,
    "storage_location": 50,
    "knowledge_collection": 45,
    "system": 35,
    "platform": 30,
}


class NexusRetrievalWarning(StrEnum):
    ENTITY_BUDGET_TRIMMED = "entity_budget_trimmed"
    RELATIONSHIP_BUDGET_TRIMMED = "relationship_budget_trimmed"
    BYTE_BUDGET_TRIMMED = "byte_budget_trimmed"
    TOKEN_BUDGET_TRIMMED = "token_budget_trimmed"
    HOP_LIMIT_TRIMMED = "hop_limit_trimmed"


class NexusRetrievalRequest(AtlasCanonicalModel):
    seed_entity_ids: tuple[str, ...] = Field(default=(), max_length=32)
    requested_entity_types: tuple[str, ...] = Field(default=(), max_length=32)
    relationship_filters: tuple[str, ...] = Field(default=(), max_length=32)
    maximum_hops: int = Field(default=1, ge=0, le=3)
    maximum_entities: int = Field(default=16, ge=0, le=256)
    maximum_relationships: int = Field(default=32, ge=0, le=512)
    maximum_bytes: int = Field(default=16_384, ge=256, le=1_000_000)
    maximum_tokens_estimate: int = Field(default=2_000, ge=16, le=128_000)
    provider_timeout_seconds: float = Field(default=1.0, gt=0, le=300.0)
    retrieval_mode: NexusRetrievalMode = NexusRetrievalMode.BALANCED

    @model_validator(mode="after")
    def normalize_inputs(self) -> "NexusRetrievalRequest":
        object.__setattr__(
            self,
            "seed_entity_ids",
            tuple(sorted(normalize_nexus_identifier(item) for item in self.seed_entity_ids)),
        )
        object.__setattr__(
            self,
            "requested_entity_types",
            tuple(sorted(normalize_nexus_identifier(item) for item in self.requested_entity_types)),
        )
        object.__setattr__(
            self,
            "relationship_filters",
            tuple(sorted(normalize_nexus_identifier(item) for item in self.relationship_filters)),
        )
        return self


class NexusEvidencePath(AtlasCanonicalModel):
    path_id: str
    entity_ids: tuple[str, ...] = Field(default=(), max_length=8)
    relationship_ids: tuple[str, ...] = Field(default=(), max_length=8)
    hop_count: int = Field(ge=0, le=3)
    explanation: str
    source_connector: str = "nexus"
    confidence_source: str = "graph_confidence"
    score: float


class NexusRetrievalExplanation(AtlasCanonicalModel):
    item_id: str
    item_kind: Literal["entity", "relationship"]
    reason: str
    score: float
    hop_count: int = Field(ge=0, le=3)


class NexusBudgetSummary(AtlasCanonicalModel):
    selected_entities: int = 0
    selected_relationships: int = 0
    discarded_entities: int = 0
    discarded_relationships: int = 0
    used_bytes: int = 0
    maximum_bytes: int
    estimated_tokens: int = 0
    maximum_tokens_estimate: int
    budget_utilization_percent: float = 0.0


class NexusRetrievalResult(AtlasCanonicalModel):
    selected_entities: tuple[NexusEntity, ...] = ()
    selected_relationships: tuple[NexusRelationship, ...] = ()
    evidence_paths: tuple[NexusEvidencePath, ...] = ()
    retrieval_explanations: tuple[NexusRetrievalExplanation, ...] = ()
    budget_summary: NexusBudgetSummary
    graph_fingerprint: str
    retrieval_fingerprint: str = ""
    warnings: tuple[NexusRetrievalWarning, ...] = ()
    average_hops: float = 0.0
    average_score: float = 0.0

    @model_validator(mode="after")
    def validate_fingerprint(self) -> "NexusRetrievalResult":
        expected = self.computed_fingerprint()
        if self.retrieval_fingerprint and self.retrieval_fingerprint != expected:
            raise ValueError("Nexus retrieval fingerprint is invalid.")
        return self

    def computed_fingerprint(self) -> str:
        payload = self.canonical_dict()
        payload["retrieval_fingerprint"] = ""
        return fingerprint(payload)

    def to_graph_result(self) -> NexusGraphResult:
        graph = NexusGraphResult(
            entities=self.selected_entities,
            relationships=self.selected_relationships,
            confidence=100,
            source_references=tuple(item.source_reference for item in self.selected_entities)
            + tuple(item.source_reference for item in self.selected_relationships),
            graph_version=NEXUS_GRAPH_VERSION,
        )
        return graph.model_copy(update={"graph_fingerprint": graph.computed_fingerprint()})


class _Candidate(AtlasCanonicalModel):
    item_id: str
    item_kind: Literal["entity", "relationship"]
    score: float
    hop_count: int
    path_entity_ids: tuple[str, ...] = ()
    path_relationship_ids: tuple[str, ...] = ()


class NexusRetrievalEngine:
    def __init__(
        self,
        *,
        relationship_weights: dict[str, int] | None = None,
        entity_weights: dict[str, int] | None = None,
    ) -> None:
        self.relationship_weights = dict(relationship_weights or RELATIONSHIP_PRIORITY_WEIGHTS)
        self.entity_weights = dict(entity_weights or ENTITY_PRIORITY_WEIGHTS)

    def retrieve(self, snapshot: NexusGraphSnapshot, request: NexusRetrievalRequest) -> NexusRetrievalResult:
        entity_candidates, relationship_candidates = self._traverse(snapshot, request)
        ranked_entities = sorted(entity_candidates.values(), key=self._candidate_order)
        ranked_relationships = sorted(relationship_candidates.values(), key=self._candidate_order)
        selected_entities, selected_relationships, warnings = self._optimize_budget(
            snapshot,
            request,
            ranked_entities,
            ranked_relationships,
        )
        explanations = self._explanations(selected_entities, selected_relationships, entity_candidates, relationship_candidates)
        paths = self._paths(explanations, entity_candidates, relationship_candidates)
        estimated_tokens = self._estimate_tokens(selected_entities, selected_relationships)
        used_bytes = len(self._payload_bytes(selected_entities, selected_relationships))
        budget = NexusBudgetSummary(
            selected_entities=len(selected_entities),
            selected_relationships=len(selected_relationships),
            discarded_entities=max(0, len(ranked_entities) - len(selected_entities)),
            discarded_relationships=max(0, len(ranked_relationships) - len(selected_relationships)),
            used_bytes=used_bytes,
            maximum_bytes=request.maximum_bytes,
            estimated_tokens=estimated_tokens,
            maximum_tokens_estimate=request.maximum_tokens_estimate,
            budget_utilization_percent=round((used_bytes / request.maximum_bytes) * 100, 3) if request.maximum_bytes else 0.0,
        )
        average_hops = round(
            sum(item.hop_count for item in tuple(entity_candidates.values()) + tuple(relationship_candidates.values()))
            / max(len(entity_candidates) + len(relationship_candidates), 1),
            3,
        )
        average_score = round(sum(item.score for item in explanations) / max(len(explanations), 1), 3)
        result = NexusRetrievalResult(
            selected_entities=selected_entities,
            selected_relationships=selected_relationships,
            evidence_paths=paths,
            retrieval_explanations=explanations,
            budget_summary=budget,
            graph_fingerprint=snapshot.graph_fingerprint,
            warnings=tuple(sorted(set(warnings), key=lambda item: item.value)),
            average_hops=average_hops,
            average_score=average_score,
        )
        return result.model_copy(update={"retrieval_fingerprint": result.computed_fingerprint()})

    def _traverse(
        self,
        snapshot: NexusGraphSnapshot,
        request: NexusRetrievalRequest,
    ) -> tuple[dict[str, _Candidate], dict[str, _Candidate]]:
        seeds = request.seed_entity_ids or tuple(entity.entity_id for entity in snapshot.entities[:1])
        if request.requested_entity_types:
            typed = tuple(entity.entity_id for entity in snapshot.entities if entity.entity_type in request.requested_entity_types)
            seeds = tuple(sorted(set(seeds) | set(typed)))
        entity_candidates: dict[str, _Candidate] = {}
        relationship_candidates: dict[str, _Candidate] = {}
        queue: list[tuple[str, int, tuple[str, ...], tuple[str, ...]]] = [
            (seed, 0, (seed,), ()) for seed in sorted(seeds) if snapshot.entity_by_id(seed) is not None
        ]
        seen_depth: dict[str, int] = {}
        while queue:
            entity_id, hop, path_entities, path_relationships = queue.pop(0)
            if hop > request.maximum_hops:
                continue
            if entity_id in seen_depth and seen_depth[entity_id] <= hop:
                continue
            seen_depth[entity_id] = hop
            entity = snapshot.entity_by_id(entity_id)
            if entity is None:
                continue
            entity_candidates[entity.entity_id] = max(
                entity_candidates.get(entity.entity_id, self._entity_candidate(entity, hop, path_entities, path_relationships)),
                self._entity_candidate(entity, hop, path_entities, path_relationships),
                key=lambda item: (item.score, -item.hop_count, item.item_id),
            )
            if hop == request.maximum_hops:
                continue
            relationships = tuple(sorted(snapshot.outgoing(entity_id) + snapshot.incoming(entity_id), key=lambda item: item.relationship_id))
            for relationship in relationships:
                relation_type = normalize_nexus_identifier(relationship.relationship_type)
                if request.relationship_filters and relation_type not in request.relationship_filters:
                    continue
                other_id = relationship.target_entity_id if relationship.source_entity_id == entity_id else relationship.source_entity_id
                next_entities = path_entities + (other_id,)
                next_relationships = path_relationships + (relationship.relationship_id,)
                relationship_candidates[relationship.relationship_id] = max(
                    relationship_candidates.get(relationship.relationship_id, self._relationship_candidate(relationship, hop + 1, next_entities, next_relationships)),
                    self._relationship_candidate(relationship, hop + 1, next_entities, next_relationships),
                    key=lambda item: (item.score, -item.hop_count, item.item_id),
                )
                if other_id not in path_entities:
                    queue.append((other_id, hop + 1, next_entities, next_relationships))
        return entity_candidates, relationship_candidates

    def _entity_candidate(
        self,
        entity: NexusEntity,
        hop: int,
        path_entities: tuple[str, ...],
        path_relationships: tuple[str, ...],
    ) -> _Candidate:
        priority = self.entity_weights.get(entity.entity_type, 10)
        score = priority + entity.confidence * 0.1 - hop * 20
        return _Candidate(item_id=entity.entity_id, item_kind="entity", score=round(score, 3), hop_count=hop, path_entity_ids=path_entities, path_relationship_ids=path_relationships)

    def _relationship_candidate(
        self,
        relationship: NexusRelationship,
        hop: int,
        path_entities: tuple[str, ...],
        path_relationships: tuple[str, ...],
    ) -> _Candidate:
        priority = self.relationship_weights.get(relationship.relationship_type, 10)
        score = priority + relationship.confidence * 0.1 - hop * 15
        return _Candidate(item_id=relationship.relationship_id, item_kind="relationship", score=round(score, 3), hop_count=hop, path_entity_ids=path_entities, path_relationship_ids=path_relationships)

    @staticmethod
    def _candidate_order(candidate: _Candidate) -> tuple[float, int, str]:
        return (-candidate.score, candidate.hop_count, candidate.item_id)

    def _optimize_budget(
        self,
        snapshot: NexusGraphSnapshot,
        request: NexusRetrievalRequest,
        ranked_entities: list[_Candidate],
        ranked_relationships: list[_Candidate],
    ) -> tuple[tuple[NexusEntity, ...], tuple[NexusRelationship, ...], list[NexusRetrievalWarning]]:
        warnings: list[NexusRetrievalWarning] = []
        selected_entities: list[NexusEntity] = []
        selected_relationships: list[NexusRelationship] = []
        for candidate in ranked_entities:
            entity = snapshot.entity_by_id(candidate.item_id)
            if entity is None:
                continue
            trial = tuple(selected_entities + [entity])
            if len(trial) > request.maximum_entities:
                warnings.append(NexusRetrievalWarning.ENTITY_BUDGET_TRIMMED)
                continue
            if self._within_payload_budget(trial, tuple(selected_relationships), request):
                selected_entities.append(entity)
            else:
                warnings.append(NexusRetrievalWarning.BYTE_BUDGET_TRIMMED)
        for candidate in ranked_relationships:
            relationship = snapshot.relationships_by_ids((candidate.item_id,))
            if not relationship:
                continue
            item = relationship[0]
            trial = tuple(selected_relationships + [item])
            if len(trial) > request.maximum_relationships:
                warnings.append(NexusRetrievalWarning.RELATIONSHIP_BUDGET_TRIMMED)
                continue
            endpoint_ids = {entity.entity_id for entity in selected_entities}
            missing_entities = [
                snapshot.entity_by_id(entity_id)
                for entity_id in (item.source_entity_id, item.target_entity_id)
                if entity_id not in endpoint_ids
            ]
            entity_trial = tuple(selected_entities + [entity for entity in missing_entities if entity is not None])
            if len(entity_trial) > request.maximum_entities:
                warnings.append(NexusRetrievalWarning.ENTITY_BUDGET_TRIMMED)
                continue
            if self._within_payload_budget(entity_trial, trial, request):
                selected_entities = list(entity_trial)
                selected_relationships.append(item)
            else:
                warnings.append(NexusRetrievalWarning.BYTE_BUDGET_TRIMMED)
        return (
            tuple(sorted({entity.entity_id: entity for entity in selected_entities}.values(), key=lambda item: item.entity_id)),
            tuple(sorted({relationship.relationship_id: relationship for relationship in selected_relationships}.values(), key=lambda item: item.relationship_id)),
            warnings,
        )

    def _within_payload_budget(
        self,
        entities: tuple[NexusEntity, ...],
        relationships: tuple[NexusRelationship, ...],
        request: NexusRetrievalRequest,
    ) -> bool:
        used_bytes = len(self._payload_bytes(entities, relationships))
        if used_bytes > request.maximum_bytes:
            return False
        return self._estimate_tokens(entities, relationships) <= request.maximum_tokens_estimate

    @staticmethod
    def _payload_bytes(entities: tuple[NexusEntity, ...], relationships: tuple[NexusRelationship, ...]) -> bytes:
        return NexusGraphResult(entities=entities, relationships=relationships).canonical_bytes()

    @staticmethod
    def _estimate_tokens(entities: tuple[NexusEntity, ...], relationships: tuple[NexusRelationship, ...]) -> int:
        return max(1, len(NexusRetrievalEngine._payload_bytes(entities, relationships)) // 4)

    def _explanations(
        self,
        selected_entities: tuple[NexusEntity, ...],
        selected_relationships: tuple[NexusRelationship, ...],
        entity_candidates: dict[str, _Candidate],
        relationship_candidates: dict[str, _Candidate],
    ) -> tuple[NexusRetrievalExplanation, ...]:
        explanations: list[NexusRetrievalExplanation] = []
        for entity in selected_entities:
            candidate = entity_candidates[entity.entity_id]
            explanations.append(
                NexusRetrievalExplanation(
                    item_id=entity.entity_id,
                    item_kind="entity",
                    reason=f"entity_priority:{entity.entity_type}:hop:{candidate.hop_count}",
                    score=candidate.score,
                    hop_count=candidate.hop_count,
                )
            )
        for relationship in selected_relationships:
            candidate = relationship_candidates[relationship.relationship_id]
            explanations.append(
                NexusRetrievalExplanation(
                    item_id=relationship.relationship_id,
                    item_kind="relationship",
                    reason=f"relationship_priority:{relationship.relationship_type}:hop:{candidate.hop_count}",
                    score=candidate.score,
                    hop_count=candidate.hop_count,
                )
            )
        strongest: dict[tuple[str, str], NexusRetrievalExplanation] = {}
        for item in explanations:
            key = (item.item_kind, item.item_id)
            if key not in strongest or item.score > strongest[key].score:
                strongest[key] = item
        return tuple(sorted(strongest.values(), key=lambda item: (item.item_kind, item.item_id)))

    def _paths(
        self,
        explanations: tuple[NexusRetrievalExplanation, ...],
        entity_candidates: dict[str, _Candidate],
        relationship_candidates: dict[str, _Candidate],
    ) -> tuple[NexusEvidencePath, ...]:
        paths: dict[str, NexusEvidencePath] = {}
        for explanation in explanations:
            candidate = entity_candidates.get(explanation.item_id) if explanation.item_kind == "entity" else relationship_candidates.get(explanation.item_id)
            if candidate is None:
                continue
            path_id = fingerprint(
                {
                    "entity_ids": candidate.path_entity_ids,
                    "relationship_ids": candidate.path_relationship_ids,
                    "reason": explanation.reason,
                }
            )[:32]
            item = NexusEvidencePath(
                path_id=path_id,
                entity_ids=candidate.path_entity_ids,
                relationship_ids=candidate.path_relationship_ids,
                hop_count=candidate.hop_count,
                explanation=explanation.reason,
                source_connector="nexus",
                confidence_source="stored_graph_confidence",
                score=explanation.score,
            )
            existing = paths.get(path_id)
            if existing is None or item.score > existing.score:
                paths[path_id] = item
        return tuple(sorted(paths.values(), key=lambda item: item.path_id))


class NexusRetrievalMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.retrieval_count = 0
        self.total_latency_ms = 0.0
        self.total_hops = 0.0
        self.total_budget_utilization = 0.0
        self.total_selected_entities = 0
        self.total_selected_relationships = 0
        self.total_discarded_entities = 0
        self.total_discarded_relationships = 0
        self.total_score = 0.0
        self.last_mode = NexusRetrievalMode.BALANCED.value
        self.last_budget_used_bytes = 0

    def record(self, *, latency_ms: float, request: NexusRetrievalRequest, result: NexusRetrievalResult) -> None:
        with self._lock:
            self.retrieval_count += 1
            self.total_latency_ms += latency_ms
            self.total_hops += result.average_hops
            self.total_budget_utilization += result.budget_summary.budget_utilization_percent
            self.total_selected_entities += result.budget_summary.selected_entities
            self.total_selected_relationships += result.budget_summary.selected_relationships
            self.total_discarded_entities += result.budget_summary.discarded_entities
            self.total_discarded_relationships += result.budget_summary.discarded_relationships
            self.total_score += result.average_score
            self.last_mode = request.retrieval_mode.value
            self.last_budget_used_bytes = result.budget_summary.used_bytes

    def diagnostics(self) -> dict[str, object]:
        with self._lock:
            count = max(self.retrieval_count, 1)
            return {
                "retrieval_engine_version": NEXUS_RETRIEVAL_ENGINE_VERSION,
                "retrieval_mode": self.last_mode,
                "retrieval_count": self.retrieval_count,
                "average_retrieval_latency_ms": round(self.total_latency_ms / count, 3) if self.retrieval_count else 0.0,
                "average_hops": round(self.total_hops / count, 3) if self.retrieval_count else 0.0,
                "average_budget_utilization_percent": round(self.total_budget_utilization / count, 3) if self.retrieval_count else 0.0,
                "average_selected_entity_count": round(self.total_selected_entities / count, 3) if self.retrieval_count else 0.0,
                "average_selected_relationship_count": round(self.total_selected_relationships / count, 3) if self.retrieval_count else 0.0,
                "discarded_entity_count": self.total_discarded_entities,
                "discarded_relationship_count": self.total_discarded_relationships,
                "average_retrieval_score": round(self.total_score / count, 3) if self.retrieval_count else 0.0,
                "last_budget_used_bytes": self.last_budget_used_bytes,
            }
