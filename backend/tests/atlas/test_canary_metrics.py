import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_canary_metrics_are_aggregate(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_users", "technical_manager")
    service = AtlasShadowModeService(initialized_runtime)

    await service.route_messages(
        messages=[{"role": "system", "content": "System"}, {"role": "user", "content": "private"}],
        request_id="request-1",
        user_identifier="technical_manager",
    )
    await service.route_messages(
        messages=[{"role": "system", "content": "System"}, {"role": "user", "content": "secret"}],
        request_id="request-2",
        user_identifier="normal_user",
    )

    diagnostics = service.diagnostics()["canary"]
    assert diagnostics["eligible_requests"] == 1
    assert diagnostics["atlas_requests"] == 1
    assert diagnostics["fallback_requests"] == 1
    assert "private" not in str(diagnostics)
    assert "secret" not in str(diagnostics)
