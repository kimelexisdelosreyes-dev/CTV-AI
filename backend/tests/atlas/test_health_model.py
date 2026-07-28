from datetime import datetime, timezone

from app.observability import AtlasHealthStatus, AtlasObservabilityService, AtlasOperationalEvent


def test_health_is_healthy_without_failures() -> None:
    assert AtlasObservabilityService().snapshot().health == AtlasHealthStatus.HEALTHY


def test_health_degrades_on_provider_timeout_rate() -> None:
    service = AtlasObservabilityService()
    now = datetime.now(timezone.utc)
    service.recent_provider_executions.append(
        AtlasOperationalEvent(timestamp=now, kind="provider", latency_ms=1, success=False, timeout=True)
    )
    service.recent_provider_executions.append(
        AtlasOperationalEvent(timestamp=now, kind="provider", latency_ms=1, success=True)
    )

    assert service.snapshot().health == AtlasHealthStatus.DEGRADED


def test_health_fails_on_compilation_failure_rate() -> None:
    service = AtlasObservabilityService()
    now = datetime.now(timezone.utc)
    service.recent_compilations.append(
        AtlasOperationalEvent(timestamp=now, kind="compile", latency_ms=1, success=False)
    )

    assert service.snapshot().health == AtlasHealthStatus.FAILED
