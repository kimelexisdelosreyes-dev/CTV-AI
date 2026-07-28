from app.shadow_mode import CanaryPolicy


def test_canary_policy_decisions_repeat_100_times() -> None:
    policy = CanaryPolicy(
        canary_enabled=True,
        shadow_enabled=True,
        canary_percentage=0,
        canary_users=("developer_01",),
    )

    decisions = tuple(policy.decide("developer_01") for _ in range(100))

    assert len({decision.deterministic_fingerprint() for decision in decisions}) == 1
