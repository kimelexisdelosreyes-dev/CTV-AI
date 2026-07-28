import pytest

from app.shadow_mode import AtlasShadowModeService
from app.core.config import settings


@pytest.mark.asyncio
async def test_shadow_metrics_are_aggregate_and_safe(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_shadow_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)

    await service.execute(production_prompt="System private\n\nMemory\nsecret", request_id="request-1")

    diagnostics = service.diagnostics()
    assert diagnostics["shadow_enabled"] is True
    assert diagnostics["shadow_requests"] == 1
    assert diagnostics["shadow_compilations"] == 1
    assert diagnostics["shadow_failures"] == 0
    assert diagnostics["shadow_traces"] == 1
    assert "private" not in str(diagnostics)
    assert "secret" not in str(diagnostics)
