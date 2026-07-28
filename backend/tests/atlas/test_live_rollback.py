import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_live_flag_rollback_restores_production(monkeypatch, initialized_runtime) -> None:
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", True)
    routed, trace, _ = await service.route_messages(
        messages=messages,
        request_id="request-1",
        user_identifier="employee",
    )
    assert trace is not None
    assert routed is not messages

    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", False)
    restored, trace, decision = await service.route_messages(
        messages=messages,
        request_id="request-2",
        user_identifier="employee",
    )

    assert restored is messages
    assert trace is None
    assert decision.atlas_active is False


@pytest.mark.asyncio
async def test_emergency_disable_overrides_live(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_emergency_disabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]

    routed, trace, decision = await service.route_messages(
        messages=messages,
        request_id="request-1",
        user_identifier="employee",
    )

    assert routed is messages
    assert trace is None
    assert decision.rollback_active is True
    assert initialized_runtime.compilation_metrics.compilation_attempts == 0
