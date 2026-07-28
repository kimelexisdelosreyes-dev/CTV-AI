from app.atlas.providers.nexus import NexusProvider, NexusGraphBuilder, NexusEntity


def test_provider_receives_store_not_builder() -> None:
    provider = NexusProvider()
    assert not isinstance(provider.graph_store, NexusGraphBuilder)
    assert provider.graph_store.snapshot is not None


def test_provider_can_replace_with_immutable_snapshot() -> None:
    provider = NexusProvider()
    snapshot = NexusGraphBuilder.from_graph(
        (NexusEntity(entity_id="ops:task:x", entity_type="task", label="X", source_reference="source:x"),),
        (),
    )
    provider.graph_store.replace_snapshot(snapshot)
    assert provider.graph_store.snapshot is snapshot
