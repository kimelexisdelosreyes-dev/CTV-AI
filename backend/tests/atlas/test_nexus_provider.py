import pytest

from app.atlas.models import AtlasProviderCollectionContext, AtlasProviderRequest
from app.atlas.providers.nexus import NEXUS_PROVIDER_ID, NexusProvider


@pytest.mark.asyncio
async def test_nexus_provider_collects_standard_provider_result() -> None:
    provider = NexusProvider()

    result = await provider.collect(
        AtlasProviderRequest(request_id="request-1"),
        AtlasProviderCollectionContext(provider_id=NEXUS_PROVIDER_ID),
    )

    assert result.provider_id == NEXUS_PROVIDER_ID
    assert result.status == "success"
    assert "records" in result.data
    assert result.data["metadata"]["graph_version"] == "1.0"


@pytest.mark.asyncio
async def test_nexus_readiness_is_data_free() -> None:
    provider = NexusProvider()

    readiness = await provider.readiness_check()

    assert readiness.ready is False
    assert "knowledge_graph" in readiness.unavailable_capabilities
