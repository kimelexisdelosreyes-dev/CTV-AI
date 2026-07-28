from __future__ import annotations

import itertools
import threading
from datetime import datetime, timedelta, timezone

import pytest

from app.atlas.knowledge_evolution import (
    FreshnessCategory,
    KnowledgeCoverageEvaluator,
    KnowledgeCoveragePolicy,
    KnowledgeEvolutionError,
    KnowledgeEvolutionErrorCategory,
    KnowledgeEvolutionEvent,
    KnowledgeEvolutionEventBuffer,
    KnowledgeEvolutionEventNormalizer,
    KnowledgeEvolutionEventType,
    KnowledgeEvolutionRecommendationEngine,
    KnowledgeEvolutionRecommendationStore,
    KnowledgeEvolutionService,
    KnowledgeEvolutionSource,
    KnowledgeFeedbackCategory,
    KnowledgeFeedbackRecord,
    KnowledgeFreshnessEvaluator,
    KnowledgeFreshnessPolicy,
    KnowledgeRecommendationStatus,
    KnowledgeRecommendationType,
    RetrievalQualityEvaluator,
    RetrievalQualityPolicy,
    age_days,
)
from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from app.core.config import settings
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


@pytest.fixture(autouse=True)
def evolution_settings(monkeypatch):
    monkeypatch.setattr(settings, "ctv_one_knowledge_evolution_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_knowledge_evolution_event_capacity", 100)
    monkeypatch.setattr(settings, "ctv_one_knowledge_evolution_recommendation_capacity", 20)
    monkeypatch.setattr(settings, "ctv_one_knowledge_evolution_minimum_sample_size", 1)
    monkeypatch.setattr(settings, "ctv_one_knowledge_evolution_empty_retrieval_threshold", 0.2)
    monkeypatch.setattr(settings, "ctv_one_knowledge_evolution_budget_pressure_threshold", 80.0)


def event(event_type=KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED, *, entity_type=None, budget=10.0) -> KnowledgeEvolutionEvent:
    return KnowledgeEvolutionEvent(
        event_type=event_type,
        source_subsystem=KnowledgeEvolutionSource.RETRIEVAL,
        provider_id="nexus",
        entity_type=entity_type,
        counts={
            "selected_entity_count": 1 if event_type != KnowledgeEvolutionEventType.RETRIEVAL_EMPTY else 0,
            "selected_relationship_count": 1 if event_type != KnowledgeEvolutionEventType.RETRIEVAL_EMPTY else 0,
            "discarded_entity_count": 0,
            "discarded_relationship_count": 0,
            "evidence_path_count": 1 if event_type != KnowledgeEvolutionEventType.RETRIEVAL_EMPTY else 0,
        },
        scores={"average_hops": 1, "average_score": 50},
        budget_utilization_percent=budget,
    )


def normalized_events(*items: KnowledgeEvolutionEvent) -> tuple[KnowledgeEvolutionEvent, ...]:
    normalizer = KnowledgeEvolutionEventNormalizer()
    return tuple(normalizer.normalize(item) for item in items)


def test_evolution_events_are_immutable_content_free_and_deterministic() -> None:
    first = KnowledgeEvolutionEventNormalizer().normalize(event(entity_type="knowledge_document"))
    second = KnowledgeEvolutionEventNormalizer().normalize(event(entity_type="knowledge_document"))

    assert first.event_fingerprint == second.event_fingerprint
    with pytest.raises(Exception):
        first.provider_id = "changed"  # type: ignore[misc]
    with pytest.raises(KnowledgeEvolutionError):
        KnowledgeEvolutionEvent(event_type=KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED, source_subsystem=KnowledgeEvolutionSource.RETRIEVAL, safe_reason_category="prompt text")


def test_event_normalizer_maps_retrieval_result_without_graph_content() -> None:
    retrieval = NexusRetrievalEngine().retrieve(retrieval_snapshot(), NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=1))
    events = KnowledgeEvolutionEventNormalizer().from_retrieval_result(retrieval)
    serialized = " ".join(item.canonical_json() for item in events).lower()

    assert events[0].event_type == KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED
    assert "doc a" not in serialized
    assert "policy a" not in serialized


def test_event_buffer_evicts_oldest_and_is_thread_safe() -> None:
    buffer = KnowledgeEvolutionEventBuffer(capacity=5)
    events = normalized_events(*(event(entity_type=f"type_{index}") for index in range(20)))

    threads = [threading.Thread(target=buffer.append, args=(item,)) for item in events]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(buffer.events()) == 5
    assert buffer.utilization_percent() == 100


def test_freshness_evaluator_classifies_current_aging_stale_and_unknown() -> None:
    evaluator = KnowledgeFreshnessEvaluator()
    policy = KnowledgeFreshnessPolicy(current_days=10, aging_days=20, stale_days=30)

    assert evaluator.evaluate_age(age_days(1), policy) == FreshnessCategory.CURRENT
    assert evaluator.evaluate_age(age_days(15), policy) == FreshnessCategory.AGING
    assert evaluator.evaluate_age(age_days(40), policy) == FreshnessCategory.STALE
    assert evaluator.evaluate_age(None, policy) == FreshnessCategory.UNKNOWN


def test_coverage_evaluator_detects_isolated_entities_and_policy_gaps() -> None:
    result = KnowledgeCoverageEvaluator().evaluate(retrieval_snapshot(), KnowledgeCoveragePolicy(expected_entity_types=("knowledge_document", "missing_type")))

    assert result["entity_type_counts"]["knowledge_document"] == 1
    assert "missing_entity_type:missing_type" in result["coverage_gaps"]


def test_retrieval_quality_evaluator_detects_empty_budget_and_low_evidence() -> None:
    events = normalized_events(
        event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90),
        event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90),
    )
    result = RetrievalQualityEvaluator().evaluate(events, RetrievalQualityPolicy(empty_retrieval_threshold=0.5, budget_pressure_threshold=80))

    assert result["empty_retrieval_rate"] == 1
    assert "high_empty_retrieval_rate" in result["gaps"]
    assert "budget_pressure" in result["gaps"]


def test_feedback_contract_is_content_free_and_does_not_mutate_graph() -> None:
    feedback = KnowledgeFeedbackRecord(feedback_category=KnowledgeFeedbackCategory.MISSING_CONTEXT, provider_id="nexus", safe_entity_category="knowledge_document")
    normalized = feedback.model_copy(update={"feedback_fingerprint": feedback.computed_fingerprint()})

    assert normalized.feedback_fingerprint == normalized.computed_fingerprint()
    assert "question" not in normalized.canonical_json().lower()
    with pytest.raises(KnowledgeEvolutionError):
        KnowledgeFeedbackRecord(feedback_category=KnowledgeFeedbackCategory.NEEDS_REVIEW, administrator_role_category="password admin")


def test_recommendation_engine_is_deterministic_and_enforces_sample_size() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
    for item in normalized_events(event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90)):
        service.event_buffer.append(item)
    snapshot = service.evaluate(retrieval_snapshot())
    recommendations = KnowledgeEvolutionRecommendationEngine().evaluate(snapshot)

    assert recommendations
    assert recommendations[0].recommendation_type in {KnowledgeRecommendationType.REVIEW_HIGH_EMPTY_RETRIEVAL_RATE, KnowledgeRecommendationType.REVIEW_BUDGET_PRESSURE}
    assert recommendations == KnowledgeEvolutionRecommendationEngine().evaluate(snapshot)


def test_recommendation_store_deduplicates_and_supports_lifecycle() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
    service.event_buffer.append(KnowledgeEvolutionEventNormalizer().normalize(event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90)))
    quality = service.evaluate(retrieval_snapshot())
    recommendations = KnowledgeEvolutionRecommendationEngine().evaluate(quality)
    store = KnowledgeEvolutionRecommendationStore(capacity=5)

    store.upsert_many(recommendations)
    store.upsert_many(recommendations)
    assert store.deduplicated_count == len(recommendations)
    updated = store.transition(store.items()[0].recommendation_fingerprint, KnowledgeRecommendationStatus.ACKNOWLEDGED)
    assert updated.review_status == KnowledgeRecommendationStatus.ACKNOWLEDGED
    with pytest.raises(KnowledgeEvolutionError):
        store.transition(updated.recommendation_fingerprint, KnowledgeRecommendationStatus.OPEN)


def test_evolution_service_records_events_feedback_evaluates_and_diagnoses() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
    service.record_event(event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90))
    service.record_feedback(KnowledgeFeedbackRecord(feedback_category=KnowledgeFeedbackCategory.USEFUL_CONTEXT, provider_id="nexus"))
    quality = service.evaluate(retrieval_snapshot())

    assert quality.quality_scores.overall_knowledge_health_score is not None
    diagnostics = service.diagnostics()
    assert diagnostics["evolution_enabled"] is True
    assert diagnostics["open_recommendation_count"] >= 1


def test_quality_scores_keep_unknown_distinct_from_zero() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
    quality = service.evaluate(None)

    assert quality.quality_scores.coverage_score is None
    assert "coverage" in quality.quality_scores.unknown_categories
    assert quality.quality_scores.overall_knowledge_health_score is not None


def test_trends_report_improving_stable_degrading_and_insufficient_data() -> None:
    service = KnowledgeEvolutionService()
    assert service._trends(())["overall"] == "insufficient_data"
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    improving = tuple(
        KnowledgeEvolutionEventNormalizer().normalize(
            item.model_copy(update={"operational_timestamp": base + timedelta(minutes=index)})
        )
        for index, item in enumerate(
            (
                event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY),
                event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY),
                event(KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED),
                event(KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED),
            )
        )
    )
    assert service._trends(improving)["overall"] == "improving"


def test_gap_detection_is_category_based_without_question_or_answer_text() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
    service.record_event(event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90))
    quality = service.evaluate(None)

    assert "high_empty_retrieval_rate" in quality.gap_categories
    assert "question" not in quality.canonical_json().lower()
    assert "answer" not in quality.canonical_json().lower()


def test_retrieval_feedback_aggregation_is_by_safe_categories() -> None:
    service = KnowledgeEvolutionService()
    service.record_feedback(KnowledgeFeedbackRecord(feedback_category=KnowledgeFeedbackCategory.IRRELEVANT_CONTEXT, provider_id="nexus", safe_entity_category="project"))
    metrics = service.metrics()

    assert metrics["feedback_category_distribution"]["irrelevant_context"] == 1
    assert "administrator" not in str(metrics).lower()


def test_policy_recommendations_never_execute_actions() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
    service.record_event(event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90))
    service.evaluate(retrieval_snapshot())
    recommendation = service.recommendation_store.items()[0]
    accepted = service.update_recommendation_status(recommendation.recommendation_fingerprint, KnowledgeRecommendationStatus.ACCEPTED)

    assert accepted.review_status == KnowledgeRecommendationStatus.ACCEPTED
    assert retrieval_snapshot().graph_fingerprint == retrieval_snapshot().graph_fingerprint


def test_100_repeated_evaluations_are_identical_excluding_timestamps() -> None:
    fingerprints = set()
    diagnostics = set()
    for _ in range(100):
        service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
        service.record_event(event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90))
        quality = service.evaluate(retrieval_snapshot())
        recommendation_fingerprints = tuple(item.recommendation_fingerprint for item in service.recommendation_store.items())
        fingerprints.add((quality.snapshot_fingerprint, recommendation_fingerprints))
        payload = service.diagnostics()
        payload["last_quality_evaluation_time"] = None
        payload["last_recommendation_evaluation_time"] = None
        diagnostics.add(str(payload))
    assert len(fingerprints) == 1
    assert len(diagnostics) == 1


def test_100_event_order_permutations_are_logically_identical() -> None:
    base = (
        event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90),
        event(KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED, budget=10),
        event(KnowledgeEvolutionEventType.PROVIDER_FALLBACK, budget=20),
    )
    fingerprints = set()
    for order in itertools.islice(itertools.cycle(itertools.permutations(base)), 100):
        service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
        for item in order:
            service.record_event(item)
        fingerprints.add(service.evaluate(retrieval_snapshot()).snapshot_fingerprint)
    assert len(fingerprints) == 1


def test_concurrent_event_feedback_recommendation_operations_are_safe() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=50), recommendation_store=KnowledgeEvolutionRecommendationStore(capacity=10))

    def append_events() -> None:
        for _ in range(20):
            service.record_event(event(KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED))

    def append_feedback() -> None:
        for _ in range(20):
            service.record_feedback(KnowledgeFeedbackRecord(feedback_category=KnowledgeFeedbackCategory.USEFUL_CONTEXT, provider_id="nexus"))

    threads = [threading.Thread(target=append_events), threading.Thread(target=append_feedback)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    service.evaluate(retrieval_snapshot())
    assert len(service.event_buffer.events()) <= 50
    assert len(service.recommendation_store.items()) <= 10


def test_privacy_surfaces_do_not_expose_content_or_raw_ids() -> None:
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=20))
    service.record_event(event(KnowledgeEvolutionEventType.RETRIEVAL_EMPTY, budget=90))
    service.evaluate(retrieval_snapshot())
    text = str(service.metrics()) + str(service.diagnostics()) + " ".join(item.canonical_json() for item in service.recommendation_store.items())

    forbidden = ("prompt", "answer text", "document body", "transcript", "ocr", "doc a", "policy a", "\\\\", ":/", "traceback")
    assert not any(item in text.lower() for item in forbidden)


def test_evolution_disabled_blocks_recording(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_knowledge_evolution_enabled", False)
    service = KnowledgeEvolutionService()

    with pytest.raises(KnowledgeEvolutionError) as exc:
        service.record_event(event())
    assert exc.value.category == KnowledgeEvolutionErrorCategory.EVOLUTION_DISABLED


def test_dependency_boundary_has_no_forbidden_runtime_invocations() -> None:
    import inspect
    import app.atlas.knowledge_evolution as module

    source = inspect.getsource(module)
    forbidden = ("app.forge", "app.services.ai_router", "NexusGraphStore", "NexusIngestionService", ".collect(", "replace_snapshot", "build_and_replace", "ollama", "embedding", "vector_store")
    assert not any(item in source for item in forbidden)
