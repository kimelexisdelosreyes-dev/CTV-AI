import itertools

import pytest

from app.atlas.providers.nexus import NexusEntityInput, NexusGraphBuilder, NexusGraphImportBatch, NexusGraphInfrastructureError


def _batch(label: str) -> NexusGraphImportBatch:
    return NexusGraphImportBatch(
        source_id=f"source-{label}",
        source_fingerprint="a" * 64,
        entities=(
            NexusEntityInput(namespace="ops", entity_type="task", external_key="same", label=label, source_reference="source:same"),
        ),
    )


def test_exact_duplicate_deduplicated() -> None:
    builder = NexusGraphBuilder()
    first = _batch("Task")
    builder.add_batch(first)
    builder.add_batch(first)
    snapshot, report = builder.build()
    assert snapshot.entity_count == 1
    assert report.deduplicated_count == 1


def test_conflicting_duplicate_rejected() -> None:
    builder = NexusGraphBuilder()
    builder.add_batch(_batch("Task A"))
    builder.add_batch(_batch("Task B"))
    with pytest.raises(NexusGraphInfrastructureError):
        builder.build()


def test_duplicate_outcome_independent_of_order() -> None:
    batches = (_batch("Task"), _batch("Task"))
    fingerprints = []
    for permutation in itertools.permutations(batches):
        builder = NexusGraphBuilder()
        for batch in permutation:
            builder.add_batch(batch)
        fingerprints.append(builder.build()[0].graph_fingerprint)
    assert len(set(fingerprints)) == 1
