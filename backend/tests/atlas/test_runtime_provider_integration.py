import pytest

from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from app.core.config import settings
from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_runtime_lifecycle_gates_provider_execution(atlas_settings):
    manager = runtime_with(CollectionProvider())
    with pytest.raises(AtlasRuntimeError) as caught: await manager.execute_provider_plan(execution_request())
    assert caught.value.category == AtlasErrorCategory.COMPILER_NOT_READY
    await manager.initialize(); assert (await manager.execute_provider_plan(execution_request())).compilation_result
    await manager.shutdown()
    with pytest.raises(AtlasRuntimeError): await manager.execute_provider_plan(execution_request())


@pytest.mark.asyncio
async def test_disabled_runtime_rejects_without_provider_call(atlas_settings, monkeypatch):
    provider = CollectionProvider(); manager = runtime_with(provider); monkeypatch.setattr(settings, "ctv_one_atlas_enabled", False); await manager.initialize()
    with pytest.raises(AtlasRuntimeError): await manager.execute_provider_plan(execution_request())
    assert provider.collect_calls == 0
