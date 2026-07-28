import pytest

from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from app.atlas.models import AtlasRuntimeState
from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from app.core.config import settings
from .test_compiler_determinism import snapshot


def assert_category(manager, category):
    with pytest.raises(AtlasRuntimeError) as caught: manager.compile_context(snapshot())
    assert caught.value.category == category


def test_compile_before_startup_is_rejected(atlas_settings):
    assert_category(AtlasRuntimeManager(AtlasProviderRegistry()), AtlasErrorCategory.COMPILER_NOT_READY)


@pytest.mark.asyncio
async def test_enabled_ready_compile_and_idempotent_startup(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); compiler = manager.compiler
    await manager.initialize(); assert manager.runtime_state == AtlasRuntimeState.READY and manager.compiler is compiler
    assert manager.compile_context(snapshot()).status == "complete"


@pytest.mark.asyncio
async def test_disabled_runtime_is_dormant_and_rejects(atlas_settings, monkeypatch):
    monkeypatch.setattr(settings, "ctv_one_atlas_enabled", False); manager = AtlasRuntimeManager(AtlasProviderRegistry())
    await manager.initialize(); assert manager.compiler is None
    assert_category(manager, AtlasErrorCategory.DISABLED)


def test_stopping_runtime_rejects(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); manager._set_runtime_state(AtlasRuntimeState.STOPPING)
    assert_category(manager, AtlasErrorCategory.COMPILER_STOPPING)


@pytest.mark.asyncio
async def test_shutdown_is_idempotent_and_stopped_rejects(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); await manager.shutdown(); await manager.shutdown()
    assert manager.runtime_state == AtlasRuntimeState.STOPPED
    assert_category(manager, AtlasErrorCategory.COMPILER_NOT_READY)


@pytest.mark.asyncio
async def test_compiler_factory_failure_is_safely_failed(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry(), compiler_factory=lambda: (_ for _ in ()).throw(RuntimeError("private")))
    await manager.initialize(); assert manager.runtime_state == AtlasRuntimeState.FAILED
    assert_category(manager, AtlasErrorCategory.COMPILER_NOT_READY)
