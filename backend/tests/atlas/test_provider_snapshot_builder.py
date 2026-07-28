import pytest

from app.atlas.models import AtlasProviderResult
from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_snapshot_is_canonical_and_uses_caller_time(atlas_settings):
    result = AtlasProviderResult(provider_id="fixture_provider", data={"records":[{"id":"b"},{"id":"a"}]})
    manager = runtime_with(CollectionProvider(result=result)); await manager.initialize()
    snapshot = (await manager.execute_provider_plan(execution_request())).compilation_snapshot
    assert snapshot.compilation_time == execution_request().compilation_time
    assert [item.to_python()["id"] for item in snapshot.provider_inputs[0].records] == ["a", "b"]
    assert snapshot.metadata.to_python()["provider_plan_fingerprint"]


@pytest.mark.asyncio
async def test_snapshot_contains_no_operational_duration(atlas_settings):
    manager = runtime_with(CollectionProvider()); await manager.initialize(); snapshot = (await manager.execute_provider_plan(execution_request())).compilation_snapshot
    assert "duration" not in snapshot.canonical_json().lower()
