from app.observability import AtlasObservabilityService
from app.shadow_mode import CanaryPolicy


def test_observability_aggregates_request_modes() -> None:
    service = AtlasObservabilityService()

    service.record_decision(CanaryPolicy(shadow_enabled=True).decide("employee"))
    service.finish_request()
    service.record_decision(CanaryPolicy(canary_enabled=True, canary_users=("ai_team",)).decide("ai_team"))
    service.finish_request()
    service.record_decision(CanaryPolicy(live_enabled=True).decide("employee"))
    service.finish_request()
    service.record_decision(CanaryPolicy().decide("employee"))
    service.finish_request()

    snapshot = service.snapshot()
    assert snapshot.request_summary.total_requests == 4
    assert snapshot.request_summary.shadow_requests == 1
    assert snapshot.request_summary.canary_requests == 1
    assert snapshot.request_summary.live_requests == 1
    assert snapshot.request_summary.production_requests == 1


def test_observability_diagnostics_do_not_leak_prompt_or_provider_text(shadow_trace_factory) -> None:
    service = AtlasObservabilityService()
    trace = shadow_trace_factory("request-1")

    service.record_trace(trace)

    diagnostics = service.diagnostics()
    assert "prompt" not in str(diagnostics).lower()
    assert "provider payload" not in str(diagnostics).lower()
    assert "secret" not in str(diagnostics).lower()
