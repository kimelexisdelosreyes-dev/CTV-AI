import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_live_off_preserves_existing_behavior(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", False)
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]

    routed, trace, decision = await service.route_messages(
        messages=messages,
        request_id="request-1",
        user_identifier="normal_user",
    )

    assert routed is messages
    assert trace is None
    assert decision.atlas_active is False


@pytest.mark.asyncio
async def test_live_on_activates_atlas_for_production_user(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System\n\nMemory\nprior"}, {"role": "user", "content": "hello"}]

    routed, trace, decision = await service.route_messages(
        messages=messages,
        request_id="request-1",
        user_identifier="normal_user",
    )

    assert trace is not None
    assert decision.live_active is True
    assert decision.atlas_injected is True
    assert routed is not messages
    assert "Atlas Context" in routed[0]["content"]
    assert routed[1] == messages[1]
