import pytest

from app.atlas.models import AtlasProviderResult
from app.atlas.provider_orchestration import AtlasProviderExecutionPlan
from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_optional_failure_is_isolated_and_compilation_continues(atlas_settings):
    good = CollectionProvider("good_provider"); bad = CollectionProvider("bad_provider", fail=True)
    manager = runtime_with(good, bad); await manager.initialize()
    request = execution_request(AtlasProviderExecutionPlan(provider_id="bad_provider", capabilities=("fixture_context",)), AtlasProviderExecutionPlan(provider_id="good_provider", capabilities=("fixture_context",)))
    outcome = await manager.execute_provider_plan(request)
    assert outcome.compilation_result and [item.provider_id for item in outcome.compilation_snapshot.provider_inputs] == ["good_provider"]


@pytest.mark.asyncio
async def test_required_failure_prevents_compiler_and_later_success_works(atlas_settings):
    provider = CollectionProvider(fail=True); manager = runtime_with(provider); await manager.initialize()
    failed = await manager.execute_provider_plan(execution_request(AtlasProviderExecutionPlan(provider_id="fixture_provider", required=True, capabilities=("fixture_context",))))
    assert failed.compilation_result is None and failed.safe_error_category == "atlas_required_provider_unavailable"
    provider.fail = False
    assert (await manager.execute_provider_plan(execution_request())).compilation_result


@pytest.mark.asyncio
async def test_unknown_optional_is_deterministically_excluded(atlas_settings):
    manager = runtime_with(); await manager.initialize()
    outcome = await manager.execute_provider_plan(execution_request(AtlasProviderExecutionPlan(provider_id="missing_provider")))
    assert outcome.compilation_result and outcome.provider_operational_statuses[0].status == "unavailable"


@pytest.mark.asyncio
async def test_mixed_failure_stress_keeps_required_and_successful_inputs(atlas_settings):
    good = [CollectionProvider(f"good_{index}") for index in range(4)]
    required = CollectionProvider("required_provider", required=True)
    timeout = CollectionProvider("timeout_provider", delay=0.02)
    malformed = CollectionProvider("malformed_provider", result=AtlasProviderResult(provider_id="malformed_provider", data={"records":[{"id":"same"},{"id":"same"}]}))
    failing = CollectionProvider("failing_provider", fail=True)
    manager = runtime_with(*good, required, timeout, malformed, failing); await manager.initialize()
    plans = [AtlasProviderExecutionPlan(provider_id=item.definition.provider_id, required=item is required, timeout_ms=1 if item is timeout else 30_000, capabilities=("fixture_context",)) for item in [*good, required, timeout, malformed, failing]]
    outcome = await manager.execute_provider_plan(execution_request(*plans))
    assert outcome.compilation_result
    assert {item.provider_id for item in outcome.compilation_snapshot.provider_inputs} == {*(item.definition.provider_id for item in good), "required_provider"}
    assert manager.provider_orchestrator.metrics.safe_snapshot()["active"] == 0
