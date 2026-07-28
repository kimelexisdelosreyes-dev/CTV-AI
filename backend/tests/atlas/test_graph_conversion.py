import pytest

from app.atlas.providers.nexus import NexusGraphStore, NexusQuery, nexus_graph_to_provider_result


@pytest.mark.asyncio
async def test_graph_conversion_exposes_only_provider_output() -> None:
    graph = await NexusGraphStore().query(NexusQuery(max_entities=3, max_relationships=2, max_depth=2))

    result = nexus_graph_to_provider_result(graph)

    assert result.provider_id == "nexus"
    assert isinstance(result.data["records"], list)
    assert "entities" not in result.data
    assert "relationships" not in result.data
    assert result.data["metadata"]["graph_fingerprint"] == graph.graph_fingerprint
