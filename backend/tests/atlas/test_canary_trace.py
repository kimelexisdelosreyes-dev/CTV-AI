import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_canary_trace_records_policy_fields(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_users", "technical_manager")
    service = AtlasShadowModeService(initialized_runtime)

    _, trace, decision = await service.route_messages(
        messages=[{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}],
        request_id="request-1",
        user_identifier="technical_manager",
    )

    assert trace is not None
    assert decision.feature_source == "allowlist"
    assert trace.canary_summary.policy_decision == "atlas_active"
    assert trace.canary_summary.canary_eligible is True
    assert trace.canary_summary.feature_source == "allowlist"
    assert trace.canary_summary.atlas_active is True
    assert "technical_manager" not in trace.canonical_json()
