import pytest

from app.atlas.providers.nexus import NexusGraphLimitsExceeded, NexusGraphStore, NexusQuery
from app.core.config import settings


@pytest.mark.asyncio
async def test_graph_traversal_depth_limit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_nexus_max_traversal_depth", 1)

    with pytest.raises(NexusGraphLimitsExceeded):
        await NexusGraphStore().query(NexusQuery(max_entities=3, max_relationships=2, max_depth=2))


@pytest.mark.asyncio
async def test_graph_entity_and_relationship_limits(monkeypatch) -> None:
    store = NexusGraphStore()
    monkeypatch.setattr(settings, "ctv_one_nexus_max_entities", 1)

    with pytest.raises(NexusGraphLimitsExceeded):
        await store.query(NexusQuery(max_entities=2, max_relationships=2, max_depth=1))
