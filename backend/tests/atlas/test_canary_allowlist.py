from app.shadow_mode import CanaryDecisionAction, CanaryPolicy


def test_allowlisted_user_is_eligible_for_atlas() -> None:
    decision = CanaryPolicy(
        canary_enabled=True,
        canary_users=("technical_manager", "ai_team"),
    ).decide("Technical_Manager")

    assert decision.action == CanaryDecisionAction.ATLAS_ACTIVE
    assert decision.eligible is True
    assert decision.atlas_active is True
    assert decision.feature_source == "allowlist"


def test_normal_user_remains_production() -> None:
    decision = CanaryPolicy(
        canary_enabled=True,
        shadow_enabled=False,
        canary_users=("technical_manager",),
    ).decide("normal_user")

    assert decision.action == CanaryDecisionAction.PRODUCTION
    assert decision.atlas_active is False
    assert decision.fallback_reason == "not_eligible"
