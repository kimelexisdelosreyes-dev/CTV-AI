import pytest

from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_diagnostics_are_safe_and_bounded(atlas_settings):
    manager = runtime_with(CollectionProvider()); await manager.initialize(); await manager.execute_provider_plan(execution_request())
    status = await manager.status(); assert status["provider_orchestrator_available"] is True
    assert status["provider_orchestration_concurrency_limit"] == 4
    text = str(status).lower()
    for prohibited in ("normalized_content", "provider_config", "credential", "decision-"):
        assert prohibited not in text
