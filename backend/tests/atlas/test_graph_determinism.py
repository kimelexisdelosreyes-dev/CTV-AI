import pytest

from app.atlas.providers.nexus import NexusGraphStore, NexusQuery


@pytest.mark.asyncio
async def test_graph_queries_are_deterministic() -> None:
    store = NexusGraphStore()
    query = NexusQuery(max_entities=3, max_relationships=2, max_depth=2)

    results = [await store.query(query) for _ in range(100)]

    assert len({result.graph_fingerprint for result in results}) == 1
    assert len({result.canonical_json() for result in results}) == 1
