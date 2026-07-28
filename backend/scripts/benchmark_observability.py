from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.observability import AtlasObservabilityService
from app.shadow_mode import CanaryPolicy


def main() -> None:
    service = AtlasObservabilityService()
    decision = CanaryPolicy(live_enabled=True).decide("employee")

    started = perf_counter()
    for _ in range(1000):
        service.record_decision(decision)
        service.finish_request()
    aggregation_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    snapshot = service.snapshot()
    snapshot_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    service.diagnostics()
    diagnostics_ms = (perf_counter() - started) * 1000

    print(
        {
            "metrics_aggregation_ms": round(aggregation_ms, 3),
            "snapshot_generation_ms": round(snapshot_ms, 3),
            "health_evaluation_ms": round(snapshot_ms, 3),
            "alert_evaluation_ms": round(snapshot_ms, 3),
            "overall_overhead_ms": round(aggregation_ms + diagnostics_ms, 3),
            "health": snapshot.health.value,
        }
    )


if __name__ == "__main__":
    main()
