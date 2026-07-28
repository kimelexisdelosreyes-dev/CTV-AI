from app.observability import AtlasObservabilityService


def test_operational_snapshot_deterministic_fields_repeat() -> None:
    service = AtlasObservabilityService()

    snapshots = [service.snapshot() for _ in range(10)]
    stable = {
        (
            snapshot.health,
            snapshot.compilation_summary,
            snapshot.provider_summary,
            snapshot.forge_summary,
            snapshot.prompt_summary,
            snapshot.request_summary,
            snapshot.fallback_summary,
            snapshot.capacity_summary.peak_concurrency,
        )
        for snapshot in snapshots
    }

    assert len(stable) == 1
