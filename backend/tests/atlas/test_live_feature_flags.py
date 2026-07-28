from app.core.config import settings
from app.shadow_mode import CanaryDecisionAction, CanaryPolicy


def test_live_flag_defaults_off() -> None:
    assert settings.ctv_one_atlas_live_enabled is False


def test_shadow_has_priority_over_live() -> None:
    decision = CanaryPolicy(
        shadow_enabled=True,
        canary_enabled=False,
        live_enabled=True,
    ).decide("normal_user")

    assert decision.action == CanaryDecisionAction.SHADOW_ONLY
    assert decision.atlas_active is False
    assert decision.live_active is False
