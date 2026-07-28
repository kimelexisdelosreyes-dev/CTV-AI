import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_live_trace_records_activation_fields(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)

    _, trace, _ = await service.route_messages(
        messages=[{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}],
        request_id="request-1",
        user_identifier="employee",
    )

    assert trace is not None
    assert trace.canary_summary.policy_decision == "live_active"
    assert trace.canary_summary.feature_source == "live"
    assert trace.canary_summary.live_active is True
    assert trace.canary_summary.atlas_injected is True
    assert trace.canary_summary.rollback_active is False
    assert "hello" not in trace.canonical_json()
