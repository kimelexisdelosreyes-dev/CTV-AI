import asyncio

import pytest

from app.atlas.providers.nexus import NexusEntity, NexusGraphBuilder, NexusGraphStore, NexusQuery


@pytest.mark.asyncio
async def test_concurrent_readers_see_complete_old_or_new_snapshot() -> None:
    store = NexusGraphStore()
    replacement = NexusGraphBuilder.from_graph(
        (NexusEntity(entity_id="ops:task:new", entity_type="task", label="New", source_reference="source:new"),),
        (),
    )

    async def reader():
        result = await store.query(NexusQuery(max_entities=16, max_relationships=32, max_depth=2))
        return tuple(item.entity_id for item in result.entities)

    tasks = [asyncio.create_task(reader()) for _ in range(10)]
    store.replace_snapshot(replacement)
    results = await asyncio.gather(*tasks, reader())

    assert all(result in {("atlas", "ctv_one", "forge"), ("ops:task:new",)} for result in results)
