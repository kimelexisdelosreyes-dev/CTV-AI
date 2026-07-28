import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_emergency_disable_bypasses_atlas(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_users", "technical_manager")
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_emergency_disabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]

    routed, trace, decision = await service.route_messages(
        messages=messages,
        request_id="request-1",
        user_identifier="technical_manager",
    )

    assert routed is messages
    assert trace is None
    assert decision.rollback_active is True
    assert initialized_runtime.compilation_metrics.compilation_attempts == 0
