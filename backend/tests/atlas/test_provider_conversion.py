import pytest

from app.atlas.models import AtlasProviderBudget, AtlasProviderCollectionContext, AtlasProviderRequest
from app.atlas.providers.nexus import NEXUS_PROVIDER_ID, NexusGraphStore, NexusProvider, nexus_graph_to_provider_result
from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_retrieval_converts_to_existing_provider_output_shape() -> None:
    retrieval = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=2),
    )
    provider_result = nexus_graph_to_provider_result(retrieval.to_graph_result())

    assert provider_result.provider_id == NEXUS_PROVIDER_ID
    assert "records" in provider_result.data
    assert "entities" not in provider_result.data
    assert "relationships" not in provider_result.data


@pytest.mark.asyncio
async def test_provider_uses_retrieval_without_exposing_graph_objects() -> None:
    provider = NexusProvider(graph_store=NexusGraphStore(snapshot=retrieval_snapshot()))

    result = await provider.collect(
        AtlasProviderRequest(request_id="request_1"),
        AtlasProviderCollectionContext(
            provider_id=NEXUS_PROVIDER_ID,
            budget=AtlasProviderBudget(max_items=3, max_output_chars=4096, max_duration_seconds=1.0),
        ),
    )

    assert result.status == "success"
    assert "records" in result.data
    assert provider.metrics.diagnostics()["retrieval_count"] == 1

