from datetime import datetime, timezone

from app.observability import AtlasObservabilityService, AtlasOperationalEvent


def test_observability_ring_buffers_are_bounded() -> None:
    service = AtlasObservabilityService()
    now = datetime.now(timezone.utc)

    for index in range(1100):
        service.recent_latency.append(
            AtlasOperationalEvent(timestamp=now, kind="atlas", latency_ms=index)
        )
    for index in range(600):
        service.recent_compilations.append(
            AtlasOperationalEvent(timestamp=now, kind="compile", latency_ms=index)
        )
        service.recent_provider_executions.append(
            AtlasOperationalEvent(timestamp=now, kind="provider", latency_ms=index)
        )
        service.recent_prompt_sizes.append(
            AtlasOperationalEvent(timestamp=now, kind="prompt", total_bytes=index)
        )

    assert len(service.recent_latency) == 1000
    assert len(service.recent_compilations) == 500
    assert len(service.recent_provider_executions) == 500
    assert len(service.recent_prompt_sizes) == 500
    assert service.recent_latency[0].latency_ms == 100
