from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from threading import Lock
from time import perf_counter
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.atlas.canonical import AtlasCanonicalModel, FrozenJson, fingerprint
from app.atlas.nexus_retrieval import NexusRetrievalResult
from app.atlas.providers.nexus import NexusGraphSnapshot
from app.core.config import settings


KNOWLEDGE_EVOLUTION_ENGINE_VERSION = "1.0"
PROHIBITED_MARKERS = (
    "prompt",
    "answer text",
    "document body",
    "transcript",
    "ocr",
    "\\\\",
    ":/",
    "password",
    "credential",
    "traceback",
)


class KnowledgeEvolutionEventType(StrEnum):
    INGESTION_COMPLETED = "ingestion_completed"
    INGESTION_FAILED = "ingestion_failed"
    SOURCE_UNCHANGED = "source_unchanged"
    SOURCE_UPDATED = "source_updated"
    RETRIEVAL_COMPLETED = "retrieval_completed"
    RETRIEVAL_EMPTY = "retrieval_empty"
    RETRIEVAL_PARTIAL = "retrieval_partial"
    ENTITY_SELECTED = "entity_selected"
    ENTITY_DISCARDED = "entity_discarded"
    RELATIONSHIP_SELECTED = "relationship_selected"
    RELATIONSHIP_DISCARDED = "relationship_discarded"
    CONTEXT_DROPPED = "context_dropped"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_FALLBACK = "provider_fallback"
    ANSWER_FEEDBACK_RECORDED = "answer_feedback_recorded"
    ADMIN_REVIEW_RECORDED = "admin_review_recorded"


class KnowledgeEvolutionSource(StrEnum):
    ATLAS = "atlas"
    NEXUS = "nexus"
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    PROVIDER = "provider"
    ADMIN = "admin"


class FreshnessCategory(StrEnum):
    CURRENT = "current"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


class TrendCategory(StrEnum):
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


class KnowledgeFeedbackCategory(StrEnum):
    USEFUL_CONTEXT = "useful_context"
    IRRELEVANT_CONTEXT = "irrelevant_context"
    MISSING_CONTEXT = "missing_context"
    OUTDATED_CONTEXT = "outdated_context"
    DUPLICATE_CONTEXT = "duplicate_context"
    INCORRECT_SOURCE_LINK = "incorrect_source_link"
    ACCEPTED_RECOMMENDATION = "accepted_recommendation"
    REJECTED_RECOMMENDATION = "rejected_recommendation"
    NEEDS_REVIEW = "needs_review"


class KnowledgeRecommendationType(StrEnum):
    REINGEST_SOURCE = "reingest_source"
    REVIEW_STALE_SOURCE = "review_stale_source"
    REVIEW_CONNECTOR_HEALTH = "review_connector_health"
    REVIEW_ORPHANED_ENTITY_TYPE = "review_orphaned_entity_type"
    REVIEW_MISSING_RELATIONSHIP_POLICY = "review_missing_relationship_policy"
    REVIEW_UNUSED_KNOWLEDGE = "review_unused_knowledge"
    REVIEW_HIGH_FALLBACK_RATE = "review_high_fallback_rate"
    REVIEW_HIGH_EMPTY_RETRIEVAL_RATE = "review_high_empty_retrieval_rate"
    REVIEW_BUDGET_PRESSURE = "review_budget_pressure"
    REVIEW_DUPLICATE_CONFLICTS = "review_duplicate_conflicts"
    REVIEW_SOURCE_COVERAGE = "review_source_coverage"
    REVIEW_RETRIEVAL_PRIORITY_POLICY = "review_retrieval_priority_policy"
    NO_ACTION = "no_action"


class KnowledgeRecommendationSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class KnowledgeRecommendationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class KnowledgeRecommendationStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class KnowledgeEvolutionErrorCategory(StrEnum):
    EVOLUTION_DISABLED = "evolution_disabled"
    INVALID_EVENT = "invalid_event"
    EVENT_LIMIT_EXCEEDED = "event_limit_exceeded"
    EVENT_NORMALIZATION_FAILED = "event_normalization_failed"
    INSUFFICIENT_DATA = "insufficient_data"
    QUALITY_EVALUATION_FAILED = "quality_evaluation_failed"
    FRESHNESS_EVALUATION_FAILED = "freshness_evaluation_failed"
    COVERAGE_EVALUATION_FAILED = "coverage_evaluation_failed"
    RETRIEVAL_EVALUATION_FAILED = "retrieval_evaluation_failed"
    RECOMMENDATION_EVALUATION_FAILED = "recommendation_evaluation_failed"
    INVALID_RECOMMENDATION_TRANSITION = "invalid_recommendation_transition"
    RECOMMENDATION_NOT_FOUND = "recommendation_not_found"
    FEEDBACK_INVALID = "feedback_invalid"
    SNAPSHOT_UNAVAILABLE = "snapshot_unavailable"
    METRICS_UNAVAILABLE = "metrics_unavailable"


class KnowledgeEvolutionError(RuntimeError):
    def __init__(self, category: KnowledgeEvolutionErrorCategory) -> None:
        super().__init__(category.value)
        self.category = category


def _safe_category(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = "_".join(str(value).strip().lower().replace("-", "_").split())[:80]
    if not normalized:
        return None
    if any(marker in normalized for marker in PROHIBITED_MARKERS):
        raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.INVALID_EVENT)
    return normalized


def _timestamp() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeEvolutionEvent(AtlasCanonicalModel):
    event_type: KnowledgeEvolutionEventType
    source_subsystem: KnowledgeEvolutionSource
    graph_fingerprint_prefix: str | None = Field(default=None, max_length=16)
    provider_id: str | None = Field(default=None, max_length=80)
    connector_id: str | None = Field(default=None, max_length=80)
    entity_type: str | None = Field(default=None, max_length=80)
    relationship_type: str | None = Field(default=None, max_length=80)
    safe_outcome_category: str | None = Field(default=None, max_length=80)
    safe_reason_category: str | None = Field(default=None, max_length=80)
    counts: FrozenJson = Field(default_factory=FrozenJson)
    scores: FrozenJson = Field(default_factory=FrozenJson)
    budget_utilization_percent: float | None = Field(default=None, ge=0, le=100)
    latency_ms: float | None = Field(default=None, ge=0, le=1_000_000)
    operational_timestamp: datetime = Field(default_factory=_timestamp)
    event_fingerprint: str = ""

    @field_validator("provider_id", "connector_id", "entity_type", "relationship_type", "safe_outcome_category", "safe_reason_category", mode="before")
    @classmethod
    def normalize_categories(cls, value):
        return _safe_category(value)

    @field_validator("counts", "scores", mode="before")
    @classmethod
    def freeze_json(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)

    @model_validator(mode="after")
    def validate_fingerprint(self) -> "KnowledgeEvolutionEvent":
        expected = self.computed_fingerprint()
        if self.event_fingerprint and self.event_fingerprint != expected:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.INVALID_EVENT)
        return self

    def computed_fingerprint(self) -> str:
        payload = self.canonical_dict()
        payload["operational_timestamp"] = ""
        payload["event_fingerprint"] = ""
        return fingerprint(payload)


class KnowledgeEvolutionEventNormalizer:
    def normalize(self, event: KnowledgeEvolutionEvent) -> KnowledgeEvolutionEvent:
        normalized = event.model_copy(update={"event_fingerprint": ""})
        return normalized.model_copy(update={"event_fingerprint": normalized.computed_fingerprint()})

    def from_retrieval_result(self, result: NexusRetrievalResult, *, provider_id: str = "nexus") -> tuple[KnowledgeEvolutionEvent, ...]:
        event_type = KnowledgeEvolutionEventType.RETRIEVAL_EMPTY if not result.selected_entities and not result.selected_relationships else KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED
        events = [
            KnowledgeEvolutionEvent(
                event_type=event_type,
                source_subsystem=KnowledgeEvolutionSource.RETRIEVAL,
                graph_fingerprint_prefix=result.graph_fingerprint[:12],
                provider_id=provider_id,
                counts=FrozenJson(
                    {
                        "selected_entity_count": result.budget_summary.selected_entities,
                        "selected_relationship_count": result.budget_summary.selected_relationships,
                        "discarded_entity_count": result.budget_summary.discarded_entities,
                        "discarded_relationship_count": result.budget_summary.discarded_relationships,
                        "evidence_path_count": len(result.evidence_paths),
                    }
                ),
                scores=FrozenJson({"average_hops": result.average_hops, "average_score": result.average_score}),
                budget_utilization_percent=result.budget_summary.budget_utilization_percent,
                safe_reason_category="retrieval_completed",
            )
        ]
        for explanation in result.retrieval_explanations:
            events.append(
                KnowledgeEvolutionEvent(
                    event_type=KnowledgeEvolutionEventType.ENTITY_SELECTED if explanation.item_kind == "entity" else KnowledgeEvolutionEventType.RELATIONSHIP_SELECTED,
                    source_subsystem=KnowledgeEvolutionSource.RETRIEVAL,
                    graph_fingerprint_prefix=result.graph_fingerprint[:12],
                    provider_id=provider_id,
                    entity_type=explanation.reason.split(":", 2)[1] if explanation.item_kind == "entity" else None,
                    relationship_type=explanation.reason.split(":", 2)[1] if explanation.item_kind == "relationship" else None,
                    counts=FrozenJson({"hop_count": explanation.hop_count}),
                    scores=FrozenJson({"score": explanation.score}),
                    safe_reason_category=explanation.reason.split(":", 1)[0],
                )
            )
        return tuple(self.normalize(item) for item in events)


class KnowledgeEvolutionEventBuffer:
    def __init__(self, capacity: int | None = None) -> None:
        configured = capacity or settings.ctv_one_knowledge_evolution_event_capacity
        self.capacity = min(max(1, configured), 100_000)
        self._events: deque[KnowledgeEvolutionEvent] = deque(maxlen=self.capacity)
        self._lock = Lock()
        self.rejection_count = 0

    def append(self, event: KnowledgeEvolutionEvent) -> None:
        if not event.event_fingerprint:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.INVALID_EVENT)
        with self._lock:
            self._events.append(event)

    def events(self) -> tuple[KnowledgeEvolutionEvent, ...]:
        with self._lock:
            return tuple(sorted(self._events, key=lambda item: (item.operational_timestamp, item.event_fingerprint)))

    def utilization_percent(self) -> float:
        return round((len(self.events()) / self.capacity) * 100, 3)


class KnowledgeFreshnessPolicy(AtlasCanonicalModel):
    current_days: int = Field(default=30, ge=1, le=3650)
    aging_days: int = Field(default=90, ge=1, le=3650)
    stale_days: int = Field(default=90, ge=1, le=3650)
    unchanged_streak_stale_threshold: int = Field(default=10, ge=1, le=10_000)


class KnowledgeCoveragePolicy(AtlasCanonicalModel):
    expected_entity_types: tuple[str, ...] = ("knowledge_document", "project", "media_asset")
    expected_relationship_by_entity_type: FrozenJson = Field(default_factory=lambda: FrozenJson({"knowledge_document": ("document_in_collection",), "media_asset": ("asset_related_to",)}))

    @field_validator("expected_relationship_by_entity_type", mode="before")
    @classmethod
    def freeze_policy(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)


class RetrievalQualityPolicy(AtlasCanonicalModel):
    empty_retrieval_threshold: float = Field(default=0.2, ge=0, le=1)
    fallback_threshold: float = Field(default=0.1, ge=0, le=1)
    budget_pressure_threshold: float = Field(default=80.0, ge=0, le=100)
    discarded_ratio_threshold: float = Field(default=2.0, ge=0, le=100)
    low_evidence_threshold: float = Field(default=0.5, ge=0, le=1)


class RecommendationRulePolicy(AtlasCanonicalModel):
    rule_id: str
    recommendation_type: KnowledgeRecommendationType
    threshold: float
    minimum_sample_size: int = Field(default=10, ge=1, le=1_000_000)
    severity: KnowledgeRecommendationSeverity
    confidence: KnowledgeRecommendationConfidence = KnowledgeRecommendationConfidence.MEDIUM
    reason_codes: tuple[str, ...]
    suppression_hours: int = Field(default=24, ge=0, le=8760)


class QualityScoreGroup(AtlasCanonicalModel):
    freshness_score: int | None = Field(default=None, ge=0, le=100)
    coverage_score: int | None = Field(default=None, ge=0, le=100)
    retrieval_reliability_score: int | None = Field(default=None, ge=0, le=100)
    connector_reliability_score: int | None = Field(default=None, ge=0, le=100)
    evidence_quality_score: int | None = Field(default=None, ge=0, le=100)
    overall_knowledge_health_score: int | None = Field(default=None, ge=0, le=100)
    unknown_categories: tuple[str, ...] = ()


class KnowledgeQualitySnapshot(AtlasCanonicalModel):
    graph_fingerprint_prefix: str | None = None
    event_count: int = 0
    freshness_distribution: FrozenJson = Field(default_factory=FrozenJson)
    entity_type_counts: FrozenJson = Field(default_factory=FrozenJson)
    relationship_type_counts: FrozenJson = Field(default_factory=FrozenJson)
    isolated_entity_count: int = 0
    weakly_connected_entity_count: int = 0
    source_coverage_counts: FrozenJson = Field(default_factory=FrozenJson)
    source_ownership_gap_count: int = 0
    total_retrievals: int = 0
    empty_retrieval_rate: float = 0.0
    partial_retrieval_rate: float = 0.0
    average_selected_entity_count: float = 0.0
    average_selected_relationship_count: float = 0.0
    average_hops: float = 0.0
    average_budget_utilization: float = 0.0
    average_discarded_candidates: float = 0.0
    evidence_path_availability_rate: float = 0.0
    connector_failure_rate: float = 0.0
    provider_fallback_rate: float = 0.0
    timeout_rate: float = 0.0
    ingestion_failure_rate: float = 0.0
    snapshot_publication_failure_rate: float = 0.0
    selected_entity_type_counts: FrozenJson = Field(default_factory=FrozenJson)
    selected_relationship_type_counts: FrozenJson = Field(default_factory=FrozenJson)
    unused_entity_ratio: float = 0.0
    never_traversed_relationship_ratio: float = 0.0
    quality_scores: QualityScoreGroup = Field(default_factory=QualityScoreGroup)
    trend_categories: FrozenJson = Field(default_factory=FrozenJson)
    gap_categories: tuple[str, ...] = ()
    snapshot_fingerprint: str = ""

    @field_validator("freshness_distribution", "entity_type_counts", "relationship_type_counts", "source_coverage_counts", "selected_entity_type_counts", "selected_relationship_type_counts", "trend_categories", mode="before")
    @classmethod
    def freeze_json(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)

    @model_validator(mode="after")
    def validate_fingerprint(self) -> "KnowledgeQualitySnapshot":
        expected = self.computed_fingerprint()
        if self.snapshot_fingerprint and self.snapshot_fingerprint != expected:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.QUALITY_EVALUATION_FAILED)
        return self

    def computed_fingerprint(self) -> str:
        payload = self.canonical_dict()
        payload["snapshot_fingerprint"] = ""
        return fingerprint(payload)


class KnowledgeFreshnessEvaluator:
    def evaluate_age(self, updated_at: datetime | None, policy: KnowledgeFreshnessPolicy, *, now: datetime | None = None, unchanged_streak: int = 0) -> FreshnessCategory:
        if updated_at is None:
            return FreshnessCategory.UNKNOWN
        now = now or _timestamp()
        age_days = max(0, (now - updated_at).days)
        if unchanged_streak >= policy.unchanged_streak_stale_threshold or age_days >= policy.stale_days:
            return FreshnessCategory.STALE
        if age_days >= policy.current_days:
            return FreshnessCategory.AGING
        return FreshnessCategory.CURRENT

    def evaluate_events(self, events: tuple[KnowledgeEvolutionEvent, ...], policy: KnowledgeFreshnessPolicy) -> dict[str, int]:
        counts = Counter({item.value: 0 for item in FreshnessCategory})
        now = max((event.operational_timestamp for event in events), default=_timestamp())
        for event in events:
            category = self.evaluate_age(event.operational_timestamp, policy, now=now)
            counts[category.value] += 1
        return dict(sorted(counts.items()))


class KnowledgeCoverageEvaluator:
    def evaluate(self, snapshot: NexusGraphSnapshot | None, policy: KnowledgeCoveragePolicy) -> dict[str, object]:
        if snapshot is None:
            return {"entity_type_counts": {}, "relationship_type_counts": {}, "isolated_entity_count": 0, "coverage_gaps": ("snapshot_unavailable",)}
        entity_counts = Counter(entity.entity_type for entity in snapshot.entities)
        relationship_counts = Counter(relationship.relationship_type for relationship in snapshot.relationships)
        connected = {value for relationship in snapshot.relationships for value in (relationship.source_entity_id, relationship.target_entity_id)}
        isolated = sum(1 for entity in snapshot.entities if entity.entity_id not in connected)
        gaps: list[str] = []
        for expected in policy.expected_entity_types:
            if entity_counts.get(expected, 0) == 0:
                gaps.append(f"missing_entity_type:{expected}")
        expected_relationships = policy.expected_relationship_by_entity_type.to_python()
        for entity_type, relationship_types in sorted(expected_relationships.items()):
            if entity_counts.get(entity_type, 0) and not any(relationship_counts.get(item, 0) for item in relationship_types):
                gaps.append(f"missing_relationship_policy:{entity_type}")
        return {
            "entity_type_counts": dict(sorted(entity_counts.items())),
            "relationship_type_counts": dict(sorted(relationship_counts.items())),
            "isolated_entity_count": isolated,
            "weakly_connected_entity_count": isolated,
            "source_coverage_counts": {"source_summary_count": len(snapshot.source_summary)},
            "source_ownership_gap_count": 0 if snapshot.source_summary else snapshot.entity_count,
            "coverage_gaps": tuple(sorted(gaps)),
        }


class RetrievalQualityEvaluator:
    def evaluate(self, events: tuple[KnowledgeEvolutionEvent, ...], policy: RetrievalQualityPolicy) -> dict[str, object]:
        retrievals = [event for event in events if event.event_type in {KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED, KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, KnowledgeEvolutionEventType.RETRIEVAL_PARTIAL}]
        total = len(retrievals)
        if total == 0:
            return {"total_retrievals": 0, "empty_retrieval_rate": 0.0, "partial_retrieval_rate": 0.0, "gaps": ("insufficient_retrieval_data",)}
        empty = sum(event.event_type == KnowledgeEvolutionEventType.RETRIEVAL_EMPTY for event in retrievals)
        partial = sum(event.event_type == KnowledgeEvolutionEventType.RETRIEVAL_PARTIAL for event in retrievals)
        selected_entities = []
        selected_relationships = []
        discarded = []
        evidence = 0
        hops = []
        budgets = []
        for event in retrievals:
            counts = event.counts.to_python()
            counts = counts if isinstance(counts, dict) else {}
            scores = event.scores.to_python()
            scores = scores if isinstance(scores, dict) else {}
            selected_entities.append(int(counts.get("selected_entity_count", 0)))
            selected_relationships.append(int(counts.get("selected_relationship_count", 0)))
            discarded.append(int(counts.get("discarded_entity_count", 0)) + int(counts.get("discarded_relationship_count", 0)))
            evidence += 1 if int(counts.get("evidence_path_count", 0)) > 0 else 0
            hops.append(float(scores.get("average_hops", 0)))
            budgets.append(float(event.budget_utilization_percent or 0))
        gaps: list[str] = []
        empty_rate = empty / total
        evidence_rate = evidence / total
        if empty_rate >= policy.empty_retrieval_threshold:
            gaps.append("high_empty_retrieval_rate")
        if evidence_rate < policy.low_evidence_threshold:
            gaps.append("low_evidence_availability")
        if sum(budgets) / total >= policy.budget_pressure_threshold:
            gaps.append("budget_pressure")
        return {
            "total_retrievals": total,
            "empty_retrieval_rate": round(empty_rate, 6),
            "partial_retrieval_rate": round(partial / total, 6),
            "average_selected_entity_count": round(sum(selected_entities) / total, 6),
            "average_selected_relationship_count": round(sum(selected_relationships) / total, 6),
            "average_hops": round(sum(hops) / total, 6),
            "average_budget_utilization": round(sum(budgets) / total, 6),
            "average_discarded_candidates": round(sum(discarded) / total, 6),
            "evidence_path_availability_rate": round(evidence_rate, 6),
            "gaps": tuple(sorted(gaps)),
        }


class KnowledgeFeedbackRecord(AtlasCanonicalModel):
    feedback_category: KnowledgeFeedbackCategory
    retrieval_fingerprint: str | None = Field(default=None, max_length=64)
    graph_fingerprint_prefix: str | None = Field(default=None, max_length=16)
    provider_id: str | None = Field(default=None, max_length=80)
    safe_entity_category: str | None = Field(default=None, max_length=80)
    safe_relationship_category: str | None = Field(default=None, max_length=80)
    administrator_role_category: str | None = Field(default=None, max_length=80)
    operational_timestamp: datetime = Field(default_factory=_timestamp)
    feedback_fingerprint: str = ""

    @field_validator("provider_id", "safe_entity_category", "safe_relationship_category", "administrator_role_category", mode="before")
    @classmethod
    def normalize_categories(cls, value):
        return _safe_category(value)

    @model_validator(mode="after")
    def validate_fingerprint(self) -> "KnowledgeFeedbackRecord":
        expected = self.computed_fingerprint()
        if self.feedback_fingerprint and self.feedback_fingerprint != expected:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.FEEDBACK_INVALID)
        return self

    def computed_fingerprint(self) -> str:
        payload = self.canonical_dict()
        payload["operational_timestamp"] = ""
        payload["feedback_fingerprint"] = ""
        return fingerprint(payload)


class KnowledgeEvolutionRecommendation(AtlasCanonicalModel):
    recommendation_id: str
    recommendation_type: KnowledgeRecommendationType
    severity: KnowledgeRecommendationSeverity
    confidence: KnowledgeRecommendationConfidence
    affected_subsystem: KnowledgeEvolutionSource
    connector_id: str | None = None
    entity_type: str | None = None
    relationship_type: str | None = None
    safe_reason_codes: tuple[str, ...]
    supporting_metric_values: FrozenJson = Field(default_factory=FrozenJson)
    graph_fingerprint_prefix: str | None = None
    created_timestamp: datetime = Field(default_factory=_timestamp)
    first_detected_timestamp: datetime = Field(default_factory=_timestamp)
    most_recent_detected_timestamp: datetime = Field(default_factory=_timestamp)
    occurrence_count: int = Field(default=1, ge=1)
    review_status: KnowledgeRecommendationStatus = KnowledgeRecommendationStatus.OPEN
    recommendation_fingerprint: str = ""

    @field_validator("connector_id", "entity_type", "relationship_type", mode="before")
    @classmethod
    def normalize_categories(cls, value):
        return _safe_category(value)

    @field_validator("supporting_metric_values", mode="before")
    @classmethod
    def freeze_metrics(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)

    @model_validator(mode="after")
    def validate_fingerprint(self) -> "KnowledgeEvolutionRecommendation":
        expected = self.logical_fingerprint()
        if self.recommendation_fingerprint and self.recommendation_fingerprint != expected:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.RECOMMENDATION_EVALUATION_FAILED)
        return self

    def logical_fingerprint(self) -> str:
        payload = {
            "recommendation_type": self.recommendation_type.value,
            "affected_subsystem": self.affected_subsystem.value,
            "connector_id": self.connector_id,
            "entity_type": self.entity_type,
            "relationship_type": self.relationship_type,
            "safe_reason_codes": self.safe_reason_codes,
            "graph_fingerprint_prefix": self.graph_fingerprint_prefix,
        }
        return fingerprint(payload)


class KnowledgeEvolutionRecommendationEngine:
    def __init__(self, rules: tuple[RecommendationRulePolicy, ...] | None = None) -> None:
        self.rules = rules or self.default_rules()

    @staticmethod
    def default_rules() -> tuple[RecommendationRulePolicy, ...]:
        return (
            RecommendationRulePolicy(rule_id="rule_connector_failure", recommendation_type=KnowledgeRecommendationType.REVIEW_CONNECTOR_HEALTH, threshold=settings.ctv_one_knowledge_evolution_connector_failure_threshold, minimum_sample_size=settings.ctv_one_knowledge_evolution_minimum_sample_size, severity=KnowledgeRecommendationSeverity.CRITICAL, confidence=KnowledgeRecommendationConfidence.HIGH, reason_codes=("connector_failure_rate",)),
            RecommendationRulePolicy(rule_id="rule_empty_retrieval", recommendation_type=KnowledgeRecommendationType.REVIEW_HIGH_EMPTY_RETRIEVAL_RATE, threshold=settings.ctv_one_knowledge_evolution_empty_retrieval_threshold, minimum_sample_size=settings.ctv_one_knowledge_evolution_minimum_sample_size, severity=KnowledgeRecommendationSeverity.HIGH, confidence=KnowledgeRecommendationConfidence.HIGH, reason_codes=("empty_retrieval_rate",)),
            RecommendationRulePolicy(rule_id="rule_budget_pressure", recommendation_type=KnowledgeRecommendationType.REVIEW_BUDGET_PRESSURE, threshold=settings.ctv_one_knowledge_evolution_budget_pressure_threshold, minimum_sample_size=settings.ctv_one_knowledge_evolution_minimum_sample_size, severity=KnowledgeRecommendationSeverity.MEDIUM, confidence=KnowledgeRecommendationConfidence.MEDIUM, reason_codes=("budget_pressure",)),
            RecommendationRulePolicy(rule_id="rule_coverage_gap", recommendation_type=KnowledgeRecommendationType.REVIEW_SOURCE_COVERAGE, threshold=1, minimum_sample_size=1, severity=KnowledgeRecommendationSeverity.MEDIUM, confidence=KnowledgeRecommendationConfidence.MEDIUM, reason_codes=("coverage_gap",)),
        )

    def evaluate(self, snapshot: KnowledgeQualitySnapshot) -> tuple[KnowledgeEvolutionRecommendation, ...]:
        recommendations: list[KnowledgeEvolutionRecommendation] = []
        for rule in self.rules:
            if not self._rule_matches(rule, snapshot):
                continue
            recommendation = KnowledgeEvolutionRecommendation(
                recommendation_id=f"recommendation_{rule.rule_id}_{snapshot.graph_fingerprint_prefix or 'none'}",
                recommendation_type=rule.recommendation_type,
                severity=rule.severity,
                confidence=rule.confidence,
                affected_subsystem=self._subsystem_for(rule),
                safe_reason_codes=rule.reason_codes,
                supporting_metric_values=self._supporting_metrics(rule, snapshot),
                graph_fingerprint_prefix=snapshot.graph_fingerprint_prefix,
            )
            recommendations.append(recommendation.model_copy(update={"recommendation_fingerprint": recommendation.logical_fingerprint()}))
        return tuple(sorted(recommendations, key=self._priority_key))

    def _rule_matches(self, rule: RecommendationRulePolicy, snapshot: KnowledgeQualitySnapshot) -> bool:
        if snapshot.event_count < rule.minimum_sample_size and rule.rule_id != "rule_coverage_gap":
            return False
        if rule.rule_id == "rule_connector_failure":
            return snapshot.connector_failure_rate >= rule.threshold
        if rule.rule_id == "rule_empty_retrieval":
            return snapshot.total_retrievals >= rule.minimum_sample_size and snapshot.empty_retrieval_rate >= rule.threshold
        if rule.rule_id == "rule_budget_pressure":
            return snapshot.total_retrievals >= rule.minimum_sample_size and snapshot.average_budget_utilization >= rule.threshold
        if rule.rule_id == "rule_coverage_gap":
            return bool(snapshot.gap_categories)
        return False

    @staticmethod
    def _subsystem_for(rule: RecommendationRulePolicy) -> KnowledgeEvolutionSource:
        if "connector" in rule.rule_id:
            return KnowledgeEvolutionSource.INGESTION
        if "retrieval" in rule.rule_id or "budget" in rule.rule_id:
            return KnowledgeEvolutionSource.RETRIEVAL
        return KnowledgeEvolutionSource.NEXUS

    @staticmethod
    def _supporting_metrics(rule: RecommendationRulePolicy, snapshot: KnowledgeQualitySnapshot) -> FrozenJson:
        values = {
            "connector_failure_rate": snapshot.connector_failure_rate,
            "empty_retrieval_rate": snapshot.empty_retrieval_rate,
            "average_budget_utilization": snapshot.average_budget_utilization,
            "coverage_gap_count": len(snapshot.gap_categories),
        }
        return FrozenJson({key: values[key] for key in sorted(values) if key in set(rule.reason_codes) or key == "coverage_gap_count"})

    @staticmethod
    def _priority_key(item: KnowledgeEvolutionRecommendation) -> tuple[int, str, str, str, str, str]:
        severity_rank = {
            KnowledgeRecommendationSeverity.CRITICAL: 0,
            KnowledgeRecommendationSeverity.HIGH: 1,
            KnowledgeRecommendationSeverity.MEDIUM: 2,
            KnowledgeRecommendationSeverity.LOW: 3,
            KnowledgeRecommendationSeverity.INFO: 4,
        }
        return (
            severity_rank[item.severity],
            item.recommendation_type.value,
            item.affected_subsystem.value,
            item.connector_id or "",
            item.entity_type or "",
            item.recommendation_fingerprint,
        )


class KnowledgeEvolutionRecommendationStore:
    VALID_TRANSITIONS = {
        KnowledgeRecommendationStatus.OPEN: {KnowledgeRecommendationStatus.ACKNOWLEDGED, KnowledgeRecommendationStatus.ACCEPTED, KnowledgeRecommendationStatus.REJECTED, KnowledgeRecommendationStatus.RESOLVED, KnowledgeRecommendationStatus.EXPIRED},
        KnowledgeRecommendationStatus.ACKNOWLEDGED: {KnowledgeRecommendationStatus.ACCEPTED, KnowledgeRecommendationStatus.REJECTED, KnowledgeRecommendationStatus.RESOLVED, KnowledgeRecommendationStatus.EXPIRED},
        KnowledgeRecommendationStatus.ACCEPTED: {KnowledgeRecommendationStatus.RESOLVED, KnowledgeRecommendationStatus.EXPIRED},
        KnowledgeRecommendationStatus.REJECTED: {KnowledgeRecommendationStatus.RESOLVED, KnowledgeRecommendationStatus.EXPIRED},
        KnowledgeRecommendationStatus.RESOLVED: {KnowledgeRecommendationStatus.EXPIRED},
        KnowledgeRecommendationStatus.EXPIRED: set(),
    }

    def __init__(self, capacity: int | None = None) -> None:
        configured = capacity or settings.ctv_one_knowledge_evolution_recommendation_capacity
        self.capacity = min(max(1, configured), 10_000)
        self._items: dict[str, KnowledgeEvolutionRecommendation] = {}
        self._lock = Lock()
        self.deduplicated_count = 0

    def upsert_many(self, recommendations: tuple[KnowledgeEvolutionRecommendation, ...]) -> tuple[KnowledgeEvolutionRecommendation, ...]:
        with self._lock:
            for recommendation in recommendations:
                key = recommendation.recommendation_fingerprint
                existing = self._items.get(key)
                if existing is not None:
                    self.deduplicated_count += 1
                    self._items[key] = existing.model_copy(
                        update={
                            "most_recent_detected_timestamp": recommendation.most_recent_detected_timestamp,
                            "occurrence_count": existing.occurrence_count + 1,
                            "severity": recommendation.severity,
                            "supporting_metric_values": recommendation.supporting_metric_values,
                        }
                    )
                else:
                    self._items[key] = recommendation
            self._evict()
            return self.items()

    def transition(self, recommendation_fingerprint: str, status: KnowledgeRecommendationStatus) -> KnowledgeEvolutionRecommendation:
        with self._lock:
            item = self._items.get(recommendation_fingerprint)
            if item is None:
                raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.RECOMMENDATION_NOT_FOUND)
            if status not in self.VALID_TRANSITIONS[item.review_status]:
                raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.INVALID_RECOMMENDATION_TRANSITION)
            updated = item.model_copy(update={"review_status": status})
            self._items[recommendation_fingerprint] = updated
            return updated

    def items(self) -> tuple[KnowledgeEvolutionRecommendation, ...]:
        return tuple(sorted(self._items.values(), key=KnowledgeEvolutionRecommendationEngine._priority_key))

    def _evict(self) -> None:
        if len(self._items) <= self.capacity:
            return
        ordered = sorted(
            self._items.values(),
            key=lambda item: (
                item.review_status not in {KnowledgeRecommendationStatus.RESOLVED, KnowledgeRecommendationStatus.EXPIRED},
                item.most_recent_detected_timestamp,
                item.recommendation_fingerprint,
            ),
        )
        for item in ordered[: max(0, len(self._items) - self.capacity)]:
            self._items.pop(item.recommendation_fingerprint, None)


class KnowledgeEvolutionService:
    def __init__(
        self,
        *,
        event_buffer: KnowledgeEvolutionEventBuffer | None = None,
        recommendation_store: KnowledgeEvolutionRecommendationStore | None = None,
        normalizer: KnowledgeEvolutionEventNormalizer | None = None,
    ) -> None:
        self.event_buffer = event_buffer or KnowledgeEvolutionEventBuffer()
        self.recommendation_store = recommendation_store or KnowledgeEvolutionRecommendationStore()
        self.normalizer = normalizer or KnowledgeEvolutionEventNormalizer()
        self.freshness_policy = KnowledgeFreshnessPolicy(stale_days=settings.ctv_one_knowledge_evolution_stale_days_default)
        self.coverage_policy = KnowledgeCoveragePolicy()
        self.retrieval_policy = RetrievalQualityPolicy(
            empty_retrieval_threshold=settings.ctv_one_knowledge_evolution_empty_retrieval_threshold,
            fallback_threshold=settings.ctv_one_knowledge_evolution_fallback_threshold,
            budget_pressure_threshold=settings.ctv_one_knowledge_evolution_budget_pressure_threshold,
        )
        self.recommendation_engine = KnowledgeEvolutionRecommendationEngine()
        self.feedback_records: deque[KnowledgeFeedbackRecord] = deque(maxlen=1_000)
        self._lock = Lock()
        self.quality_snapshot_count = 0
        self.last_quality_evaluation_time: datetime | None = None
        self.last_recommendation_evaluation_time: datetime | None = None
        self.generated_count = 0

    def record_event(self, event: KnowledgeEvolutionEvent) -> KnowledgeEvolutionEvent:
        if not settings.ctv_one_knowledge_evolution_enabled:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.EVOLUTION_DISABLED)
        normalized = self.normalizer.normalize(event)
        self.event_buffer.append(normalized)
        return normalized

    def record_retrieval_result(self, result: NexusRetrievalResult) -> tuple[KnowledgeEvolutionEvent, ...]:
        events = self.normalizer.from_retrieval_result(result)
        for event in events:
            self.record_event(event)
        return events

    def record_feedback(self, feedback: KnowledgeFeedbackRecord) -> KnowledgeFeedbackRecord:
        if not settings.ctv_one_knowledge_evolution_enabled:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.EVOLUTION_DISABLED)
        normalized = feedback.model_copy(update={"feedback_fingerprint": feedback.computed_fingerprint()})
        with self._lock:
            self.feedback_records.append(normalized)
        event = KnowledgeEvolutionEvent(
            event_type=KnowledgeEvolutionEventType.ANSWER_FEEDBACK_RECORDED,
            source_subsystem=KnowledgeEvolutionSource.ADMIN,
            graph_fingerprint_prefix=normalized.graph_fingerprint_prefix,
            provider_id=normalized.provider_id,
            entity_type=normalized.safe_entity_category,
            relationship_type=normalized.safe_relationship_category,
            safe_outcome_category=normalized.feedback_category.value,
            safe_reason_category=normalized.administrator_role_category,
        )
        self.record_event(event)
        return normalized

    def evaluate(self, snapshot: NexusGraphSnapshot | None = None) -> KnowledgeQualitySnapshot:
        if not settings.ctv_one_knowledge_evolution_enabled:
            raise KnowledgeEvolutionError(KnowledgeEvolutionErrorCategory.EVOLUTION_DISABLED)
        started = perf_counter()
        events = self.event_buffer.events()
        freshness = KnowledgeFreshnessEvaluator().evaluate_events(events, self.freshness_policy)
        coverage = KnowledgeCoverageEvaluator().evaluate(snapshot, self.coverage_policy)
        retrieval = RetrievalQualityEvaluator().evaluate(events, self.retrieval_policy)
        reliability = self._reliability(events)
        selected_entity_type_counts = Counter(event.entity_type for event in events if event.event_type == KnowledgeEvolutionEventType.ENTITY_SELECTED and event.entity_type)
        selected_relationship_type_counts = Counter(event.relationship_type for event in events if event.event_type == KnowledgeEvolutionEventType.RELATIONSHIP_SELECTED and event.relationship_type)
        quality_scores = self._quality_scores(freshness, coverage, retrieval, reliability)
        trends = self._trends(events)
        gaps = tuple(sorted(set(coverage.get("coverage_gaps", ())) | set(retrieval.get("gaps", ()))))
        retrieval_fields = {key: value for key, value in retrieval.items() if key != "gaps"}
        unused_ratio = self._unused_entity_ratio(snapshot, selected_entity_type_counts)
        never_traversed_ratio = self._never_traversed_relationship_ratio(snapshot, selected_relationship_type_counts)
        quality = KnowledgeQualitySnapshot(
            graph_fingerprint_prefix=snapshot.graph_fingerprint[:12] if snapshot else None,
            event_count=len(events),
            freshness_distribution=FrozenJson(freshness),
            entity_type_counts=FrozenJson(coverage.get("entity_type_counts", {})),
            relationship_type_counts=FrozenJson(coverage.get("relationship_type_counts", {})),
            isolated_entity_count=int(coverage.get("isolated_entity_count", 0)),
            weakly_connected_entity_count=int(coverage.get("weakly_connected_entity_count", 0)),
            source_coverage_counts=FrozenJson(coverage.get("source_coverage_counts", {})),
            source_ownership_gap_count=int(coverage.get("source_ownership_gap_count", 0)),
            selected_entity_type_counts=FrozenJson(dict(sorted(selected_entity_type_counts.items()))),
            selected_relationship_type_counts=FrozenJson(dict(sorted(selected_relationship_type_counts.items()))),
            unused_entity_ratio=unused_ratio,
            never_traversed_relationship_ratio=never_traversed_ratio,
            quality_scores=quality_scores,
            trend_categories=FrozenJson(trends),
            gap_categories=gaps,
            **retrieval_fields,
            **reliability,
        )
        quality = quality.model_copy(update={"snapshot_fingerprint": quality.computed_fingerprint()})
        recommendations = self.recommendation_engine.evaluate(quality)
        self.recommendation_store.upsert_many(recommendations)
        self.generated_count += len(recommendations)
        self.quality_snapshot_count += 1
        now = _timestamp()
        self.last_quality_evaluation_time = now
        self.last_recommendation_evaluation_time = now
        _ = perf_counter() - started
        return quality

    def update_recommendation_status(self, recommendation_fingerprint: str, status: KnowledgeRecommendationStatus) -> KnowledgeEvolutionRecommendation:
        updated = self.recommendation_store.transition(recommendation_fingerprint, status)
        event = KnowledgeEvolutionEvent(
            event_type=KnowledgeEvolutionEventType.ADMIN_REVIEW_RECORDED,
            source_subsystem=KnowledgeEvolutionSource.ADMIN,
            graph_fingerprint_prefix=updated.graph_fingerprint_prefix,
            safe_outcome_category=status.value,
            safe_reason_category=updated.recommendation_type.value,
        )
        if settings.ctv_one_knowledge_evolution_enabled:
            self.event_buffer.append(self.normalizer.normalize(event))
        return updated

    def metrics(self) -> dict[str, object]:
        events = self.event_buffer.events()
        recommendations = self.recommendation_store.items()
        feedback = tuple(self.feedback_records)
        return {
            "event_count": len(events),
            "event_type_counts": dict(sorted(Counter(event.event_type.value for event in events).items())),
            "buffer_utilization_percent": self.event_buffer.utilization_percent(),
            "event_rejection_count": self.event_buffer.rejection_count,
            "quality_snapshot_count": self.quality_snapshot_count,
            "recommendation_generated_count": self.generated_count,
            "recommendation_deduplicated_count": self.recommendation_store.deduplicated_count,
            "open_count": sum(item.review_status == KnowledgeRecommendationStatus.OPEN for item in recommendations),
            "accepted_count": sum(item.review_status == KnowledgeRecommendationStatus.ACCEPTED for item in recommendations),
            "rejected_count": sum(item.review_status == KnowledgeRecommendationStatus.REJECTED for item in recommendations),
            "resolved_count": sum(item.review_status == KnowledgeRecommendationStatus.RESOLVED for item in recommendations),
            "expired_count": sum(item.review_status == KnowledgeRecommendationStatus.EXPIRED for item in recommendations),
            "severity_distribution": dict(sorted(Counter(item.severity.value for item in recommendations).items())),
            "recommendation_type_distribution": dict(sorted(Counter(item.recommendation_type.value for item in recommendations).items())),
            "feedback_count": len(feedback),
            "feedback_category_distribution": dict(sorted(Counter(item.feedback_category.value for item in feedback).items())),
        }

    def diagnostics(self) -> dict[str, object]:
        recommendations = self.recommendation_store.items()
        metrics = self.metrics()
        return {
            "evolution_enabled": settings.ctv_one_knowledge_evolution_enabled,
            "service_status": "ready",
            "engine_version": KNOWLEDGE_EVOLUTION_ENGINE_VERSION,
            "event_buffer_size": len(self.event_buffer.events()),
            "event_capacity": self.event_buffer.capacity,
            "recommendation_store_size": len(recommendations),
            "recommendation_capacity": self.recommendation_store.capacity,
            "last_quality_evaluation_time": self.last_quality_evaluation_time.isoformat() if self.last_quality_evaluation_time else None,
            "last_recommendation_evaluation_time": self.last_recommendation_evaluation_time.isoformat() if self.last_recommendation_evaluation_time else None,
            "overall_health_category": self._overall_health_category(recommendations),
            "open_recommendation_count": metrics["open_count"],
            "recommendation_severity_distribution": metrics["severity_distribution"],
            "stale_source_aggregate_count": 0,
            "coverage_gap_aggregate_count": sum(1 for item in recommendations if item.recommendation_type == KnowledgeRecommendationType.REVIEW_SOURCE_COVERAGE),
            "empty_retrieval_aggregate_rate": self._last_rate(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY),
            "connector_failure_aggregate_rate": self._last_rate(KnowledgeEvolutionEventType.INGESTION_FAILED),
        }

    def _reliability(self, events: tuple[KnowledgeEvolutionEvent, ...]) -> dict[str, float]:
        total = max(len(events), 1)
        return {
            "connector_failure_rate": round(sum(event.event_type == KnowledgeEvolutionEventType.INGESTION_FAILED for event in events) / total, 6),
            "provider_fallback_rate": round(sum(event.event_type == KnowledgeEvolutionEventType.PROVIDER_FALLBACK for event in events) / total, 6),
            "timeout_rate": round(sum(event.event_type == KnowledgeEvolutionEventType.PROVIDER_TIMEOUT for event in events) / total, 6),
            "ingestion_failure_rate": round(sum(event.event_type == KnowledgeEvolutionEventType.INGESTION_FAILED for event in events) / total, 6),
            "snapshot_publication_failure_rate": 0.0,
        }

    def _quality_scores(self, freshness: dict[str, int], coverage: dict[str, object], retrieval: dict[str, object], reliability: dict[str, float]) -> QualityScoreGroup:
        total_freshness = sum(freshness.values())
        freshness_score = None if total_freshness == 0 else max(0, 100 - int((freshness.get("stale", 0) / total_freshness) * 100))
        entity_counts = coverage.get("entity_type_counts", {})
        coverage_score = None if not entity_counts else max(0, 100 - int(int(coverage.get("isolated_entity_count", 0)) / max(sum(entity_counts.values()), 1) * 100))
        retrieval_total = int(retrieval.get("total_retrievals", 0))
        retrieval_score = None if retrieval_total == 0 else max(0, 100 - int(float(retrieval.get("empty_retrieval_rate", 0)) * 100))
        connector_score = max(0, 100 - int(reliability["connector_failure_rate"] * 100))
        evidence_score = None if retrieval_total == 0 else int(float(retrieval.get("evidence_path_availability_rate", 0)) * 100)
        known = [score for score in (freshness_score, coverage_score, retrieval_score, connector_score, evidence_score) if score is not None]
        unknown = tuple(name for name, score in (("freshness", freshness_score), ("coverage", coverage_score), ("retrieval", retrieval_score), ("connector", connector_score), ("evidence", evidence_score)) if score is None)
        return QualityScoreGroup(
            freshness_score=freshness_score,
            coverage_score=coverage_score,
            retrieval_reliability_score=retrieval_score,
            connector_reliability_score=connector_score,
            evidence_quality_score=evidence_score,
            overall_knowledge_health_score=round(sum(known) / len(known)) if known else None,
            unknown_categories=unknown,
        )

    def _trends(self, events: tuple[KnowledgeEvolutionEvent, ...]) -> dict[str, str]:
        if len(events) < 4:
            return {"overall": TrendCategory.INSUFFICIENT_DATA.value}
        ordered = sorted(events, key=lambda item: (item.operational_timestamp, item.event_fingerprint))
        midpoint = len(ordered) // 2
        first_failures = sum(event.event_type in {KnowledgeEvolutionEventType.INGESTION_FAILED, KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, KnowledgeEvolutionEventType.PROVIDER_FALLBACK} for event in ordered[:midpoint]) / max(midpoint, 1)
        second_failures = sum(event.event_type in {KnowledgeEvolutionEventType.INGESTION_FAILED, KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, KnowledgeEvolutionEventType.PROVIDER_FALLBACK} for event in ordered[midpoint:]) / max(len(ordered) - midpoint, 1)
        if second_failures < first_failures:
            trend = TrendCategory.IMPROVING
        elif second_failures > first_failures:
            trend = TrendCategory.DEGRADING
        else:
            trend = TrendCategory.STABLE
        return {"overall": trend.value}

    def _unused_entity_ratio(self, snapshot: NexusGraphSnapshot | None, selected: Counter) -> float:
        if snapshot is None or snapshot.entity_count == 0:
            return 0.0
        selected_total = sum(min(count, sum(1 for entity in snapshot.entities if entity.entity_type == entity_type)) for entity_type, count in selected.items())
        return round(max(0, snapshot.entity_count - selected_total) / snapshot.entity_count, 6)

    def _never_traversed_relationship_ratio(self, snapshot: NexusGraphSnapshot | None, selected: Counter) -> float:
        if snapshot is None or snapshot.relationship_count == 0:
            return 0.0
        selected_total = sum(min(count, sum(1 for relationship in snapshot.relationships if relationship.relationship_type == relationship_type)) for relationship_type, count in selected.items())
        return round(max(0, snapshot.relationship_count - selected_total) / snapshot.relationship_count, 6)

    def _overall_health_category(self, recommendations: tuple[KnowledgeEvolutionRecommendation, ...]) -> str:
        if any(item.severity == KnowledgeRecommendationSeverity.CRITICAL and item.review_status == KnowledgeRecommendationStatus.OPEN for item in recommendations):
            return "critical"
        if any(item.severity == KnowledgeRecommendationSeverity.HIGH and item.review_status == KnowledgeRecommendationStatus.OPEN for item in recommendations):
            return "degraded"
        return "stable"

    def _last_rate(self, event_type: KnowledgeEvolutionEventType) -> float:
        events = self.event_buffer.events()
        return round(sum(event.event_type == event_type for event in events) / max(len(events), 1), 6)


def age_days(days: int) -> datetime:
    return _timestamp() - timedelta(days=days)
