import asyncio

import pytest

from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_twenty_concurrent_orchestrations_are_isolated(atlas_settings):
    manager = runtime_with(CollectionProvider()); await manager.initialize()
    outcomes = await asyncio.gather(*(manager.execute_provider_plan(execution_request()) for _ in range(20)))
    assert len({item.compilation_result.deterministic_digest for item in outcomes}) == 1
    assert manager.provider_orchestrator.metrics.safe_snapshot()["active"] == 0
