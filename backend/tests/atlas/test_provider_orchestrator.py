import pytest

from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_selected_provider_executes_once_and_compiles(atlas_settings):
    provider = CollectionProvider(); manager = runtime_with(provider); await manager.initialize()
    outcome = await manager.execute_provider_plan(execution_request())
    assert provider.collect_calls == 1 and outcome.compilation_snapshot and outcome.compilation_result
    assert outcome.compilation_result.status == "complete"


@pytest.mark.asyncio
async def test_provider_receives_only_narrow_request_and_context(atlas_settings):
    provider = CollectionProvider(); manager = runtime_with(provider); await manager.initialize(); await manager.execute_provider_plan(execution_request())
    assert provider.last_request.request_id == "request-1"
    assert provider.last_context.provider_id == "fixture_provider"
    assert not hasattr(provider.last_request, "runtime_manager")
