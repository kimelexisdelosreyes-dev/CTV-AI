from app.observability import AtlasObservabilityService
from app.shadow_mode import CanaryPolicy


def test_capacity_metrics_are_measured() -> None:
    service = AtlasObservabilityService()
    decision = CanaryPolicy(live_enabled=True).decide("employee")
    service.record_decision(decision)
    service.finish_request()

    capacity = service.snapshot().capacity_summary

    assert capacity.requests_per_hour > 0
    assert capacity.peak_concurrency == 1
    assert capacity.atlas_utilization == 100
