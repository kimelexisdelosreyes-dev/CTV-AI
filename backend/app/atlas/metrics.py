from __future__ import annotations

from collections import Counter, defaultdict
from threading import Lock


class AtlasRuntimeMetrics:
    """Process-local bounded Atlas metrics with registry-owned labels only."""

    def __init__(self) -> None:
        self._counters: Counter[tuple[str, str, str]] = Counter()
        self._gauges: dict[tuple[str, str, str, str], float] = {}
        self._durations: dict[tuple[str, str], list[float]] = defaultdict(list)
        self._lock = Lock()

    def increment(
        self,
        name: str,
        *,
        provider_id: str = "runtime",
        reason_category: str = "",
    ) -> None:
        with self._lock:
            self._counters[(name, provider_id, reason_category)] += 1

    def gauge(
        self,
        name: str,
        value: float,
        *,
        provider_id: str = "runtime",
        lifecycle_state: str = "",
        health_status: str = "",
    ) -> None:
        with self._lock:
            self._gauges[(name, provider_id, lifecycle_state, health_status)] = value

    def duration(self, name: str, value: float, *, provider_id: str = "runtime") -> None:
        with self._lock:
            values = self._durations[(name, provider_id)]
            values.append(max(float(value), 0.0))
            del values[:-100]

    def safe_snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": {
                    f"{name}:{provider_id}:{reason_category}": value
                    for (name, provider_id, reason_category), value in sorted(self._counters.items())
                },
                "gauges": {
                    f"{name}:{provider_id}:{lifecycle_state}:{health_status}": value
                    for (name, provider_id, lifecycle_state, health_status), value in sorted(
                        self._gauges.items()
                    )
                },
            }


atlas_runtime_metrics = AtlasRuntimeMetrics()
