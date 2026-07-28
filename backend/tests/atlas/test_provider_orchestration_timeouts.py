import pytest

from app.atlas.provider_orchestration import AtlasProviderExecutionPlan
from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_optional_timeout_is_sanitized_and_isolated(atlas_settings):
    provider = CollectionProvider(delay=0.02); manager = runtime_with(provider); await manager.initialize()
    outcome = await manager.execute_provider_plan(execution_request(AtlasProviderExecutionPlan(provider_id="fixture_provider", timeout_ms=1, capabilities=("fixture_context",))))
    assert outcome.compilation_result and outcome.provider_operational_statuses[0].status == "timeout"
    assert outcome.provider_operational_statuses[0].safe_error_category == "atlas_provider_timeout"


@pytest.mark.asyncio
async def test_required_timeout_prevents_compilation(atlas_settings):
    provider = CollectionProvider(delay=0.02); manager = runtime_with(provider); await manager.initialize()
    outcome = await manager.execute_provider_plan(execution_request(AtlasProviderExecutionPlan(provider_id="fixture_provider", required=True, timeout_ms=1, capabilities=("fixture_context",))))
    assert outcome.compilation_result is None and outcome.safe_error_category == "atlas_required_provider_unavailable"
