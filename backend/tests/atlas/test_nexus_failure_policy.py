import pytest

from app.atlas.models import AtlasProviderCollectionContext, AtlasProviderRequest
from app.atlas.providers.nexus import NexusGraphLimitsExceeded, NexusProvider


class LimitStore:
    async def query(self, query):
        raise NexusGraphLimitsExceeded("nexus_entity_limit_exceeded")


@pytest.mark.asyncio
async def test_nexus_limit_failure_is_partial_and_isolated() -> None:
    provider = NexusProvider(graph_store=LimitStore())

    result = await provider.collect(
        AtlasProviderRequest(request_id="request-1"),
        AtlasProviderCollectionContext(provider_id="nexus"),
    )

    assert result.status == "partial"
    assert result.warnings == ("nexus_entity_limit_exceeded",)
    assert provider.metrics.diagnostics()["success_rate"] == 0
