import pytest

from app.atlas.providers.nexus import NexusGraphBuilder, NexusGraphImportBatch, NexusRelationshipInput, NexusEntityInput, NexusGraphInfrastructureError


def test_orphan_relationship_rejected() -> None:
    relationship = NexusRelationshipInput(
        namespace="ops",
        source_namespace="ops",
        source_entity_type="task",
        source_external_key="a",
        relationship_type="blocks",
        target_namespace="ops",
        target_entity_type="task",
        target_external_key="missing",
        source_reference="source:rel",
    )
    batch = NexusGraphImportBatch(
        source_id="source",
        source_fingerprint="a" * 64,
        entities=(NexusEntityInput(namespace="ops", entity_type="task", external_key="a", label="A", source_reference="source:a"),),
        relationships=(relationship,),
    )
    builder = NexusGraphBuilder()
    builder.add_batch(batch)
    with pytest.raises(NexusGraphInfrastructureError):
        builder.build()


def test_self_reference_rejected() -> None:
    with pytest.raises(Exception):
        NexusRelationshipInput(
            namespace="ops",
            source_namespace="ops",
            source_entity_type="task",
            source_external_key="a",
            relationship_type="related",
            target_namespace="ops",
            target_entity_type="task",
            target_external_key="a",
            source_reference="source:rel",
        )
