import pytest

from app.atlas.models import AtlasProviderCollectionContext, AtlasProviderRequest
from app.atlas.providers.nexus import NexusProvider


@pytest.mark.asyncio
async def test_nexus_metrics_are_aggregate_and_safe() -> None:
    provider = NexusProvider()

    await provider.collect(
        AtlasProviderRequest(request_id="request-1"),
        AtlasProviderCollectionContext(provider_id="nexus"),
    )

    diagnostics = provider.metrics.diagnostics()
    assert diagnostics["query_count"] == 1
    assert diagnostics["success_rate"] == 100
    assert diagnostics["average_entity_count"] > 0
    assert "CTV ONE" not in str(diagnostics)
    assert "supports" not in str(diagnostics)
