from app.atlas.providers.nexus import NexusEntity, NexusGraphBuilder, NexusGraphStore


def test_store_holds_one_active_snapshot_and_reports_readiness() -> None:
    store = NexusGraphStore()
    original = store.snapshot
    replacement = NexusGraphBuilder.from_graph(
        (NexusEntity(entity_id="ops:task:x", entity_type="task", label="X", source_reference="source:x"),),
        (),
    )

    store.replace_snapshot(replacement)

    assert store.ready is True
    assert store.snapshot is replacement
    assert original is not replacement
