from __future__ import annotations

import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.atlas.knowledge_evolution import (
    KnowledgeEvolutionEvent,
    KnowledgeEvolutionEventBuffer,
    KnowledgeEvolutionEventNormalizer,
    KnowledgeEvolutionEventType,
    KnowledgeEvolutionService,
    KnowledgeEvolutionSource,
    KnowledgeFeedbackCategory,
    KnowledgeFeedbackRecord,
)
from app.atlas.providers.nexus import NexusEntity, NexusGraphBuilder, NexusRelationship
from app.core.config import settings


def build_snapshot(entity_count: int, relationship_count: int):
    settings.ctv_one_nexus_max_entities = entity_count + 10
    settings.ctv_one_nexus_max_relationships = relationship_count + 10
    settings.ctv_one_nexus_max_relationships_per_entity = relationship_count + 10
    settings.ctv_one_nexus_max_snapshot_bytes = 500_000_000
    settings.ctv_one_nexus_max_build_seconds = 60.0
    entities = tuple(
        NexusEntity(
            entity_id=f"node_{index:06d}",
            entity_type=("knowledge_document" if index % 3 == 0 else "project" if index % 3 == 1 else "media_asset"),
            label=f"Node {index}",
            source_reference=f"nexus:node_{index:06d}",
        )
        for index in range(entity_count)
    )
    relationships = tuple(
        NexusRelationship(
            relationship_id=f"rel_{index:06d}",
            source_entity_id=f"node_{index % entity_count:06d}",
            target_entity_id=f"node_{(index + 1) % entity_count:06d}",
            relationship_type=("document_in_collection" if index % 3 == 0 else "document_relates_to_project" if index % 3 == 1 else "asset_related_to"),
            source_reference=f"nexus:rel_{index:06d}",
        )
        for index in range(relationship_count)
    )
    return NexusGraphBuilder.from_graph(entities, relationships)


def make_event(index: int) -> KnowledgeEvolutionEvent:
    event_type = (
        KnowledgeEvolutionEventType.RETRIEVAL_EMPTY
        if index % 10 == 0
        else KnowledgeEvolutionEventType.PROVIDER_FALLBACK
        if index % 29 == 0
        else KnowledgeEvolutionEventType.INGESTION_FAILED
        if index % 53 == 0
        else KnowledgeEvolutionEventType.RETRIEVAL_COMPLETED
    )
    return KnowledgeEvolutionEvent(
        event_type=event_type,
        source_subsystem=KnowledgeEvolutionSource.RETRIEVAL,
        provider_id="nexus",
        entity_type=("knowledge_document" if index % 3 == 0 else "project"),
        relationship_type=("document_in_collection" if index % 2 == 0 else "asset_related_to"),
        counts={
            "selected_entity_count": 0 if event_type == KnowledgeEvolutionEventType.RETRIEVAL_EMPTY else 4,
            "selected_relationship_count": 0 if event_type == KnowledgeEvolutionEventType.RETRIEVAL_EMPTY else 3,
            "discarded_entity_count": index % 5,
            "discarded_relationship_count": index % 7,
            "evidence_path_count": 0 if event_type == KnowledgeEvolutionEventType.RETRIEVAL_EMPTY else 3,
        },
        scores={"average_hops": index % 3, "average_score": 50 + (index % 40)},
        budget_utilization_percent=float(index % 100),
        latency_ms=float(index % 250),
    )


def measure(fn):
    started = perf_counter()
    value = fn()
    return value, (perf_counter() - started) * 1000


def run_case(name: str, event_count: int, entity_count: int, relationship_count: int, feedback_count: int) -> dict[str, float | int]:
    settings.ctv_one_knowledge_evolution_enabled = True
    settings.ctv_one_knowledge_evolution_event_capacity = max(event_count, 1)
    settings.ctv_one_knowledge_evolution_recommendation_capacity = 1_000
    settings.ctv_one_knowledge_evolution_minimum_sample_size = 10
    snapshot = build_snapshot(entity_count, relationship_count)
    normalizer = KnowledgeEvolutionEventNormalizer()
    service = KnowledgeEvolutionService(event_buffer=KnowledgeEvolutionEventBuffer(capacity=event_count))

    events, normalization_ms = measure(lambda: tuple(normalizer.normalize(make_event(index)) for index in range(event_count)))
    _, append_ms = measure(lambda: [service.event_buffer.append(event) for event in events])
    _, feedback_ms = measure(
        lambda: [
            service.feedback_records.append(
                KnowledgeFeedbackRecord(feedback_category=KnowledgeFeedbackCategory.USEFUL_CONTEXT, provider_id="nexus").model_copy(update={"feedback_fingerprint": "f" * 64})
            )
            for _ in range(feedback_count)
        ]
    )
    quality, snapshot_ms = measure(lambda: service.evaluate(snapshot))
    _, diagnostics_ms = measure(service.diagnostics)
    recommendations = service.recommendation_store.items()
    total_ms = normalization_ms + append_ms + feedback_ms + snapshot_ms + diagnostics_ms
    return {
        "events": event_count,
        "entities": entity_count,
        "relationships": relationship_count,
        "event_normalization_ms": round(normalization_ms, 3),
        "event_append_ms": round(append_ms, 3),
        "snapshot_build_ms": round(snapshot_ms, 3),
        "freshness_evaluation_ms": round(snapshot_ms, 3),
        "coverage_evaluation_ms": round(snapshot_ms, 3),
        "retrieval_quality_evaluation_ms": round(snapshot_ms, 3),
        "recommendation_generation_ms": round(snapshot_ms, 3),
        "feedback_aggregation_ms": round(feedback_ms, 3),
        "diagnostics_ms": round(diagnostics_ms, 3),
        "events_per_second": round(event_count / max(total_ms / 1000, 0.001), 3),
        "memory_estimate_bytes": len(quality.canonical_bytes()) + sum(len(item.canonical_bytes()) for item in recommendations),
        "buffer_utilization_percent": service.event_buffer.utilization_percent(),
        "recommendation_count": len(recommendations),
        "median_ms": round(statistics.median([normalization_ms, append_ms, snapshot_ms, diagnostics_ms]), 3),
        "p95_ms": round(sorted([normalization_ms, append_ms, snapshot_ms, diagnostics_ms])[-1], 3),
    }


def main() -> None:
    print(
        {
            "small": run_case("small", 1_000, 100, 300, 100),
            "moderate": run_case("moderate", 10_000, 5_000, 15_000, 1_000),
        }
    )


if __name__ == "__main__":
    main()

