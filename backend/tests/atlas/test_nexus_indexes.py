import pytest

from app.atlas.providers.nexus import NexusGraphStore, NexusQuery


@pytest.mark.asyncio
async def test_indexes_return_canonical_relationship_order() -> None:
    snapshot = NexusGraphStore().snapshot
    assert snapshot is not None
    outgoing_ids = tuple(item.relationship_id for item in snapshot.outgoing("forge"))
    incoming_ids = tuple(item.relationship_id for item in snapshot.incoming("atlas"))
    assert outgoing_ids == tuple(sorted(outgoing_ids))
    assert incoming_ids == tuple(sorted(incoming_ids))


@pytest.mark.asyncio
async def test_equivalent_graphs_produce_identical_query_output() -> None:
    store = NexusGraphStore()
    first = await store.query(NexusQuery(max_entities=3, max_relationships=2, max_depth=2))
    second = await store.query(NexusQuery(max_entities=3, max_relationships=2, max_depth=2))
    assert first.graph_fingerprint == second.graph_fingerprint
