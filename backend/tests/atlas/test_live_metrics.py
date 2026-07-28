import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_live_metrics_are_recorded(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)

    await service.route_messages(
        messages=[{"role": "system", "content": "System"}, {"role": "user", "content": "secret"}],
        request_id="request-1",
        user_identifier="employee",
    )

    diagnostics = service.diagnostics()["canary"]
    assert diagnostics["live_enabled"] is True
    assert diagnostics["live_requests"] == 1
    assert diagnostics["atlas_injections"] == 1
    assert diagnostics["atlas_failures"] == 0
    assert diagnostics["average_retained_nodes"] == 0
    assert "secret" not in str(diagnostics)
