from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.atlas.providers.nexus import (
    NexusEntityInput,
    NexusGraphBuilder,
    NexusGraphImportBatch,
    NexusGraphStore,
    NexusQuery,
    NexusRelationshipInput,
)
from app.core.config import settings


def _batch(entity_count: int, relationship_count: int) -> NexusGraphImportBatch:
    entities = tuple(
        NexusEntityInput(
            namespace="bench",
            entity_type="node",
            external_key=str(index),
            label=f"Node {index}",
            source_reference=f"bench:{index}",
        )
        for index in range(entity_count)
    )
    relationships = []
    for index in range(relationship_count):
        relationships.append(
            NexusRelationshipInput(
                namespace="bench",
                source_namespace="bench",
                source_entity_type="node",
                source_external_key=str(index % entity_count),
                relationship_type="links",
                target_namespace="bench",
                target_entity_type="node",
                target_external_key=str((index + 1) % entity_count),
                discriminator=str(index),
                source_reference=f"bench:rel:{index}",
            )
        )
    return NexusGraphImportBatch(
        source_id="benchmark",
        source_fingerprint="a" * 64,
        entities=entities,
        relationships=tuple(relationships),
    )


def _measure(entity_count: int, relationship_count: int) -> dict[str, object]:
    settings.ctv_one_nexus_max_entities = max(settings.ctv_one_nexus_max_entities, entity_count)
    settings.ctv_one_nexus_max_relationships = max(settings.ctv_one_nexus_max_relationships, relationship_count)
    settings.ctv_one_nexus_max_relationships_per_entity = max(settings.ctv_one_nexus_max_relationships_per_entity, relationship_count)
    settings.ctv_one_nexus_max_snapshot_bytes = max(settings.ctv_one_nexus_max_snapshot_bytes, 100_000_000)
    batch_started = perf_counter()
    batch = _batch(entity_count, relationship_count)
    validation_ms = (perf_counter() - batch_started) * 1000

    builder = NexusGraphBuilder()
    identity_started = perf_counter()
    builder.add_batch(batch)
    identity_ms = (perf_counter() - identity_started) * 1000

    build_times = []
    index_ms = 0.0
    snapshot = None
    for _ in range(3):
        started = perf_counter()
        snapshot, _ = builder.build()
        elapsed = (perf_counter() - started) * 1000
        build_times.append(elapsed)
        index_ms = elapsed

    assert snapshot is not None
    serialization_started = perf_counter()
    snapshot_bytes = len(snapshot.canonical_bytes())
    serialization_ms = (perf_counter() - serialization_started) * 1000

    fingerprint_started = perf_counter()
    snapshot.computed_fingerprint()
    fingerprint_ms = (perf_counter() - fingerprint_started) * 1000

    store = NexusGraphStore(snapshot=snapshot)
    replacement_started = perf_counter()
    store.replace_snapshot(snapshot)
    replacement_ms = (perf_counter() - replacement_started) * 1000

    query_started = perf_counter()
    import asyncio

    asyncio.run(store.query(NexusQuery(max_entities=min(entity_count, 16), max_relationships=min(relationship_count, 32), max_depth=2)))
    query_ms = (perf_counter() - query_started) * 1000

    return {
        "entities": entity_count,
        "relationships": relationship_count,
        "import_validation_ms": round(validation_ms, 3),
        "identity_generation_ms": round(identity_ms, 3),
        "duplicate_detection_ms": round(statistics.median(build_times), 3),
        "relationship_validation_ms": round(statistics.median(build_times), 3),
        "index_build_ms": round(index_ms, 3),
        "snapshot_serialization_ms": round(serialization_ms, 3),
        "fingerprint_generation_ms": round(fingerprint_ms, 3),
        "snapshot_replacement_ms": round(replacement_ms, 3),
        "query_latency_ms": round(query_ms, 3),
        "median_build_ms": round(statistics.median(build_times), 3),
        "p95_build_ms": round(max(build_times), 3),
        "total_build_ms": round(sum(build_times), 3),
        "snapshot_bytes": snapshot_bytes,
        "memory_estimate_bytes": sys.getsizeof(snapshot.canonical_bytes()),
    }


def main() -> None:
    random.seed(1)
    print({"small": _measure(100, 300), "moderate": _measure(5_000, 15_000)})


if __name__ == "__main__":
    main()
