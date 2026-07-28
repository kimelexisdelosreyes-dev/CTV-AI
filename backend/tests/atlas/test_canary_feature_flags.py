from app.core.config import settings
from app.shadow_mode import CanaryPolicy


def test_canary_feature_flag_defaults() -> None:
    assert settings.ctv_one_atlas_shadow_enabled is False
    assert settings.ctv_one_atlas_canary_enabled is False
    assert settings.ctv_one_atlas_live_enabled is False
    assert settings.ctv_one_atlas_canary_percentage == 0


def test_percentage_framework_disabled_at_zero() -> None:
    policy = CanaryPolicy(
        canary_enabled=True,
        canary_percentage=0,
        canary_users=(),
    )

    assert policy.decide("developer_01").atlas_active is False
