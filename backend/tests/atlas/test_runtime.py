from __future__ import annotations

import asyncio

import pytest

from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from app.atlas.lifecycle import transition_record
from app.atlas.models import (
    AtlasProviderLifecycleState,
    AtlasProviderRuntimeRecord,
    AtlasRuntimeState,
)
from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from app.core.config import settings

from .conftest import FakeAtlasProvider


def manager_for(*providers: FakeAtlasProvider) -> AtlasRuntimeManager:
    registry = AtlasProviderRegistry()
    for provider in providers:
        registry.register(provider)
    return AtlasRuntimeManager(registry)


@pytest.mark.asyncio
async def test_empty_runtime_initializes_ready_and_shuts_down(atlas_settings) -> None:
    manager = manager_for()
    await manager.initialize()
    status = await manager.status()
    assert manager.runtime_state == AtlasRuntimeState.READY
    assert status["registered_provider_count"] == 0
    assert status["runtime_ready"] is True
    await manager.shutdown()
    await manager.shutdown()
    assert manager.runtime_state == AtlasRuntimeState.STOPPED


@pytest.mark.asyncio
async def test_disabled_runtime_does_not_initialize_providers(atlas_settings, monkeypatch) -> None:
    provider = FakeAtlasProvider()
    manager = manager_for(provider)
    monkeypatch.setattr(settings, "ctv_one_atlas_enabled", False)
    await manager.initialize()
    assert provider.initialize_calls == 0
    assert manager.records["fixture_provider"].state == AtlasProviderLifecycleState.DISABLED
    status = await manager.status()
    assert status["atlas_enabled"] is False
    assert status["runtime_ready"] is False


@pytest.mark.asyncio
async def test_double_initialization_idempotent_shutdown_and_controlled_restart(atlas_settings) -> None:
    provider = FakeAtlasProvider()
    manager = manager_for(provider)
    await manager.initialize()
    await manager.initialize()
    assert provider.initialize_calls == 1
    await manager.shutdown()
    await manager.shutdown()
    assert provider.shutdown_calls == 1
    await manager.initialize()
    assert provider.initialize_calls == 2


@pytest.mark.asyncio
async def test_optional_and_required_initialization_failures_are_isolated(atlas_settings) -> None:
    optional = FakeAtlasProvider("optional_provider")
    optional.fail_initialize = True
    manager = manager_for(optional)
    await manager.initialize()
    assert manager.runtime_state == AtlasRuntimeState.READY
    assert manager.records["optional_provider"].state == AtlasProviderLifecycleState.FAILED

    required = FakeAtlasProvider("required_provider", required=True)
    required.fail_initialize = True
    manager = manager_for(required)
    await manager.initialize()
    assert manager.runtime_state == AtlasRuntimeState.DEGRADED
    assert manager.required_provider_failures == ["required_provider"]


@pytest.mark.asyncio
async def test_initialization_and_shutdown_timeouts_are_categorized(atlas_settings, monkeypatch) -> None:
    provider = FakeAtlasProvider()
    provider.initialize_delay = 0.02
    monkeypatch.setattr(settings, "ctv_one_atlas_initialize_timeout_seconds", 0.001)
    manager = manager_for(provider)
    await manager.initialize()
    record = manager.records["fixture_provider"]
    assert record.state == AtlasProviderLifecycleState.FAILED
    assert record.failure_reason_category == AtlasErrorCategory.PROVIDER_TIMEOUT.value

    provider = FakeAtlasProvider()
    provider.shutdown_delay = 0.02
    monkeypatch.setattr(settings, "ctv_one_atlas_shutdown_timeout_seconds", 0.001)
    manager = manager_for(provider)
    await manager.initialize()
    await manager.shutdown()
    assert manager.records["fixture_provider"].failure_reason_category == AtlasErrorCategory.PROVIDER_TIMEOUT.value
    assert manager.records["fixture_provider"].state == AtlasProviderLifecycleState.STOPPED


@pytest.mark.asyncio
async def test_health_threshold_recovery_and_disabled_polling(atlas_settings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_failure_threshold", 2)
    monkeypatch.setattr(settings, "ctv_one_atlas_recovery_threshold", 2)
    provider = FakeAtlasProvider()
    manager = manager_for(provider)
    await manager.initialize()
    provider.fail_health = True
    await manager.health_check("fixture_provider")
    assert manager.records["fixture_provider"].state == AtlasProviderLifecycleState.DEGRADED
    await manager.health_check("fixture_provider")
    assert manager.records["fixture_provider"].state == AtlasProviderLifecycleState.UNAVAILABLE
    provider.fail_health = False
    await manager.health_check("fixture_provider")
    await manager.health_check("fixture_provider")
    assert manager.records["fixture_provider"].state == AtlasProviderLifecycleState.READY

    manager.transition("fixture_provider", AtlasProviderLifecycleState.DRAINING)
    calls = provider.health_calls
    await manager.health_check("fixture_provider")
    assert provider.health_calls == calls


@pytest.mark.asyncio
async def test_required_health_failure_and_diagnostics_remain_safe(atlas_settings) -> None:
    provider = FakeAtlasProvider(required=True)
    manager = manager_for(provider)
    await manager.initialize()
    provider.fail_health = True
    await manager.health_check("fixture_provider")
    status = await manager.status()
    assert manager.runtime_state == AtlasRuntimeState.DEGRADED
    assert status["required_provider_failures"] == ["fixture_provider"]
    assert "private health failure" not in str(status).lower()


@pytest.mark.asyncio
async def test_readiness_failure_is_safe_and_health_task_is_cancelled(atlas_settings, monkeypatch) -> None:
    provider = FakeAtlasProvider()
    provider.fail_readiness = True
    manager = manager_for(provider)
    await manager.initialize()
    record = manager.records["fixture_provider"]
    assert record.state == AtlasProviderLifecycleState.DEGRADED
    assert record.failure_reason_category == AtlasErrorCategory.PROVIDER_READINESS_FAILED.value

    provider = FakeAtlasProvider()
    manager = manager_for(provider)
    monkeypatch.setattr(settings, "ctv_one_atlas_health_poll_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_health_poll_seconds", 0.001)
    await manager.initialize()
    assert manager._health_task is not None
    await asyncio.sleep(0.01)
    await manager.shutdown()
    assert manager._health_task is None


def test_lifecycle_accepts_required_transitions_and_rejects_illegal_ones() -> None:
    record = AtlasProviderRuntimeRecord(definition=FakeAtlasProvider().definition)
    transition_record(record, AtlasProviderLifecycleState.INITIALIZING)
    transition_record(record, AtlasProviderLifecycleState.READY)
    transition_record(record, AtlasProviderLifecycleState.DEGRADED)
    transition_record(record, AtlasProviderLifecycleState.UNAVAILABLE)
    transition_record(record, AtlasProviderLifecycleState.DRAINING)
    transition_record(record, AtlasProviderLifecycleState.STOPPED)
    assert record.previous_state == AtlasProviderLifecycleState.DRAINING
    with pytest.raises(AtlasRuntimeError) as invalid:
        transition_record(record, AtlasProviderLifecycleState.READY)
    assert invalid.value.category == AtlasErrorCategory.INVALID_LIFECYCLE_TRANSITION


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (AtlasProviderLifecycleState.REGISTERED, AtlasProviderLifecycleState.INITIALIZING),
        (AtlasProviderLifecycleState.REGISTERED, AtlasProviderLifecycleState.DISABLED),
        (AtlasProviderLifecycleState.INITIALIZING, AtlasProviderLifecycleState.READY),
        (AtlasProviderLifecycleState.INITIALIZING, AtlasProviderLifecycleState.DEGRADED),
        (AtlasProviderLifecycleState.INITIALIZING, AtlasProviderLifecycleState.UNAVAILABLE),
        (AtlasProviderLifecycleState.INITIALIZING, AtlasProviderLifecycleState.FAILED),
        (AtlasProviderLifecycleState.READY, AtlasProviderLifecycleState.DEGRADED),
        (AtlasProviderLifecycleState.READY, AtlasProviderLifecycleState.UNAVAILABLE),
        (AtlasProviderLifecycleState.READY, AtlasProviderLifecycleState.DRAINING),
        (AtlasProviderLifecycleState.DEGRADED, AtlasProviderLifecycleState.READY),
        (AtlasProviderLifecycleState.DEGRADED, AtlasProviderLifecycleState.UNAVAILABLE),
        (AtlasProviderLifecycleState.DEGRADED, AtlasProviderLifecycleState.DRAINING),
        (AtlasProviderLifecycleState.UNAVAILABLE, AtlasProviderLifecycleState.READY),
        (AtlasProviderLifecycleState.UNAVAILABLE, AtlasProviderLifecycleState.DEGRADED),
        (AtlasProviderLifecycleState.UNAVAILABLE, AtlasProviderLifecycleState.DRAINING),
        (AtlasProviderLifecycleState.DISABLED, AtlasProviderLifecycleState.STOPPED),
        (AtlasProviderLifecycleState.DRAINING, AtlasProviderLifecycleState.STOPPED),
        (AtlasProviderLifecycleState.FAILED, AtlasProviderLifecycleState.STOPPED),
    ],
)
def test_every_declared_lifecycle_transition_is_valid(source, target) -> None:
    record = AtlasProviderRuntimeRecord(definition=FakeAtlasProvider().definition, state=source)
    transition_record(record, target)
    assert record.state == target
