from datetime import datetime, timezone

from app.core.config import settings
from app.observability import AtlasObservabilityService, AtlasOperationalEvent


def test_alerts_include_slow_compile() -> None:
    service = AtlasObservabilityService()
    service.recent_compilations.append(
        AtlasOperationalEvent(timestamp=datetime.now(timezone.utc), kind="compile", latency_ms=150)
    )

    assert "average_compile_latency_high" in service.snapshot().alerts


def test_alerts_include_emergency_disable(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_emergency_disabled", True)

    assert "emergency_disable_active" in AtlasObservabilityService().snapshot().alerts
