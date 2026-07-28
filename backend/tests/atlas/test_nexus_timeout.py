import asyncio

import pytest

from app.atlas.models import AtlasProviderCollectionContext, AtlasProviderRequest
from app.atlas.providers.nexus import NexusGraphResult, NexusProvider
from app.core.config import settings


class SlowStore:
    async def query(self, query):
        await asyncio.sleep(0.01)
        return NexusGraphResult()


@pytest.mark.asyncio
async def test_nexus_timeout_returns_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_nexus_max_execution_seconds", 0.001)
    provider = NexusProvider(graph_store=SlowStore())

    result = await provider.collect(
        AtlasProviderRequest(request_id="request-1"),
        AtlasProviderCollectionContext(provider_id="nexus"),
    )

    assert result.status == "unavailable"
    assert result.safe_error_category == "nexus_timeout"
    assert provider.metrics.diagnostics()["timeout_count"] == 1
