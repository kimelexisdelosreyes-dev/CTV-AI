from app.atlas.providers.nexus import NexusEntityInput, NexusGraphImportBatch, NexusProvider


def test_graph_observability_records_builds_without_content() -> None:
    provider = NexusProvider()
    batch = NexusGraphImportBatch(
        source_id="source",
        source_fingerprint="a" * 64,
        entities=(NexusEntityInput(namespace="ops", entity_type="task", external_key="x", label="Secret Project", source_reference="source:x"),),
    )

    provider.build_and_replace_snapshot((batch,))

    diagnostics = provider.metrics.diagnostics()
    assert diagnostics["successful_builds"] == 1
    assert diagnostics["snapshot_replacements"] == 1
    assert "secret project" not in str(diagnostics).lower()
