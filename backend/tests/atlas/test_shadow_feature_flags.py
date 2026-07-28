import pytest

from app.shadow_mode import AtlasShadowModeService
from app.core.config import settings


@pytest.mark.asyncio
async def test_shadow_disabled_returns_no_trace(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_shadow_enabled", False)
    service = AtlasShadowModeService(initialized_runtime)

    trace = await service.execute(production_prompt="System\n\nMemory\nx", request_id="request-1")

    assert trace is None
    assert service.diagnostics()["shadow_requests"] == 0


def test_canary_and_live_flags_are_reserved_defaults() -> None:
    assert settings.ctv_one_atlas_shadow_enabled is False
    assert settings.ctv_one_atlas_canary_enabled is False
    assert settings.ctv_one_atlas_live_enabled is False
