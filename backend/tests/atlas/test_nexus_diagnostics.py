import pytest

from app.atlas.models import AtlasProviderCollectionContext, AtlasProviderRequest
from app.atlas.providers.nexus import NexusProvider


@pytest.mark.asyncio
async def test_nexus_diagnostics_exclude_graph_contents() -> None:
    provider = NexusProvider()
    await provider.collect(
        AtlasProviderRequest(request_id="request-1"),
        AtlasProviderCollectionContext(provider_id="nexus"),
    )

    diagnostics = provider.metrics.diagnostics()
    serialized = str(diagnostics).lower()
    assert diagnostics["graph_version"] == "1.0"
    assert "entities" not in serialized
    assert "relationships" not in serialized
    assert "atlas" not in serialized
