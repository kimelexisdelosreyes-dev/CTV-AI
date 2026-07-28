from app.atlas.providers.nexus import NexusEntityInput, NexusGraphBuilder, NexusGraphImportBatch


def test_graph_fingerprint_excludes_operational_data() -> None:
    batch = NexusGraphImportBatch(
        source_id="source",
        source_fingerprint="a" * 64,
        entities=(NexusEntityInput(namespace="ops", entity_type="task", external_key="x", label="X", source_reference="source:x"),),
    )
    builder = NexusGraphBuilder()
    builder.add_batch(batch)
    first = builder.build()[0]
    second = builder.build()[0]
    assert first.graph_fingerprint == second.graph_fingerprint
    assert first.canonical_bytes() == second.canonical_bytes()
