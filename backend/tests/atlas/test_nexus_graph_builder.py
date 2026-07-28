import pytest

from app.atlas.providers.nexus import (
    NexusEntityInput,
    NexusGraphBuilder,
    NexusGraphImportBatch,
    NexusGraphInfrastructureError,
    NexusRelationshipInput,
)


def _entity(key: str, label: str | None = None) -> NexusEntityInput:
    return NexusEntityInput(
        namespace="ops",
        entity_type="task",
        external_key=key,
        label=label or f"Task {key}",
        source_reference=f"source:{key}",
    )


def _batch(*entities, relationships=()) -> NexusGraphImportBatch:
    return NexusGraphImportBatch(source_id="source", source_fingerprint="a" * 64, entities=entities, relationships=relationships)


def test_valid_graph_builds_snapshot() -> None:
    relationship = NexusRelationshipInput(
        namespace="ops",
        source_namespace="ops",
        source_entity_type="task",
        source_external_key="a",
        relationship_type="blocks",
        target_namespace="ops",
        target_entity_type="task",
        target_external_key="b",
        source_reference="source:rel",
    )
    builder = NexusGraphBuilder()
    builder.add_batch(_batch(_entity("a"), _entity("b"), relationships=(relationship,)))
    snapshot, report = builder.build()
    assert snapshot.entity_count == 2
    assert snapshot.relationship_count == 1
    assert report.deduplicated_count == 0


def test_invalid_graph_rejected() -> None:
    relationship = NexusRelationshipInput(
        namespace="ops",
        source_namespace="ops",
        source_entity_type="task",
        source_external_key="missing",
        relationship_type="blocks",
        target_namespace="ops",
        target_entity_type="task",
        target_external_key="b",
        source_reference="source:rel",
    )
    builder = NexusGraphBuilder()
    builder.add_batch(_batch(_entity("b"), relationships=(relationship,)))
    with pytest.raises(NexusGraphInfrastructureError):
        builder.build()
