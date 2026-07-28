import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_allowlisted_user_receives_atlas_prompt(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_users", "technical_manager")
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]

    routed, trace, decision = await service.route_messages(
        messages=messages,
        request_id="request-1",
        user_identifier="technical_manager",
    )

    assert trace is not None
    assert decision.atlas_active is True
    assert routed is not messages
    assert "Atlas Context" in routed[0]["content"]
    assert messages[0]["content"] == "System"


@pytest.mark.asyncio
async def test_non_canary_user_prompt_unchanged(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_users", "technical_manager")
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
