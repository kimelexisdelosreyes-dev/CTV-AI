from app.shadow_mode import CanaryDecisionAction, CanaryPolicy


def test_canary_policy_defaults_to_production() -> None:
    decision = CanaryPolicy(
        canary_enabled=False,
        shadow_enabled=False,
        canary_users=(),
    ).decide("technical_manager")

    assert decision.action == CanaryDecisionAction.PRODUCTION
    assert decision.eligible is False
    assert decision.atlas_active is False
    assert decision.feature_source == "canary_disabled"


def test_canary_policy_emergency_disable_has_priority() -> None:
    decision = CanaryPolicy(
        canary_enabled=True,
        canary_users=("technical_manager",),
        emergency_disabled=True,
    ).decide("technical_manager")

    assert decision.action == CanaryDecisionAction.ROLLBACK
    assert decision.rollback_active is True
    assert decision.atlas_active is False
    assert decision.fallback_reason == "emergency_disabled"
