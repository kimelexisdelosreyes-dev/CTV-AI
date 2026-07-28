from __future__ import annotations

import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from app.atlas.providers.nexus import NexusEntity, NexusGraphBuilder, NexusRelationship, nexus_graph_to_provider_result
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
            confidence=100 - (index % 20),
        )
        for index in range(entity_count)
    )
    relationships = tuple(
        NexusRelationship(
            relationship_id=f"rel_{index:06d}",
            source_entity_id=f"node_{index % entity_count:06d}",
            target_entity_id=f"node_{(index + 1) % entity_count:06d}",
            relationship_type=("direct_reference" if index % 3 == 0 else "document_relates_to_project" if index % 3 == 1 else "asset_related_to"),
            source_reference=f"nexus:rel_{index:06d}",
            confidence=100 - (index % 30),
        )
        for index in range(relationship_count)
    )
    return NexusGraphBuilder.from_graph(entities, relationships)


def measure(fn):
    started = perf_counter()
    value = fn()
    return value, (perf_counter() - started) * 1000


def run_case(entity_count: int, relationship_count: int) -> dict[str, float | int]:
    snapshot = build_snapshot(entity_count, relationship_count)
    engine = NexusRetrievalEngine()
    request = NexusRetrievalRequest(
        seed_entity_ids=("node_000000",),
        maximum_hops=3,
        maximum_entities=64,
        maximum_relationships=128,
        maximum_bytes=64_000,
        maximum_tokens_estimate=16_000,
    )
    retrieval_times = []
    conversion_times = []
    for _ in range(7):
        result, retrieval_ms = measure(lambda: engine.retrieve(snapshot, request))
        _, conversion_ms = measure(lambda: nexus_graph_to_provider_result(result.to_graph_result()))
        retrieval_times.append(retrieval_ms)
        conversion_times.append(conversion_ms)
    return {
        "entities": entity_count,
        "relationships": relationship_count,
        "retrieval_median_ms": round(statistics.median(retrieval_times), 3),
        "retrieval_p95_ms": round(sorted(retrieval_times)[int((len(retrieval_times) - 1) * 0.95)], 3),
        "ranking_and_budget_ms": round(statistics.median(retrieval_times), 3),
        "provider_conversion_median_ms": round(statistics.median(conversion_times), 3),
        "total_latency_median_ms": round(statistics.median([a + b for a, b in zip(retrieval_times, conversion_times)]), 3),
        "selected_entities": result.budget_summary.selected_entities,
        "selected_relationships": result.budget_summary.selected_relationships,
        "budget_utilization_percent": result.budget_summary.budget_utilization_percent,
    }


def main() -> None:
    print({"small": run_case(100, 300), "moderate": run_case(5_000, 15_000)})


if __name__ == "__main__":
    main()

