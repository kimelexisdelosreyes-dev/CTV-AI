from datetime import datetime, timezone

from app.observability import AtlasObservabilityService, AtlasOperationalEvent


def test_latency_histogram_buckets() -> None:
    service = AtlasObservabilityService()
    now = datetime.now(timezone.utc)
    for value in (1, 7, 20, 40, 80, 120):
        service.recent_latency.append(AtlasOperationalEvent(timestamp=now, kind="atlas", latency_ms=value))

    histogram = service.latency_histogram()

    assert histogram == {
        "lt_5ms": 1,
        "5_10ms": 1,
        "10_25ms": 1,
        "25_50ms": 1,
        "50_100ms": 1,
        "100ms_plus": 1,
    }


def test_moving_averages_are_windowed() -> None:
    service = AtlasObservabilityService()
    now = datetime.now(timezone.utc)
    service.recent_latency.append(AtlasOperationalEvent(timestamp=now, kind="compile", latency_ms=10))
    service.recent_latency.append(AtlasOperationalEvent(timestamp=now, kind="compile", latency_ms=20))

    summary = service.snapshot().latency_summary

    assert summary.compile_moving_average_1m == 15
