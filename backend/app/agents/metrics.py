from __future__ import annotations

from collections import Counter, defaultdict
from threading import Lock


class AgentRuntimeMetrics:
    """Process-local bounded metrics; labels are registry-owned stable IDs only."""

    def __init__(self) -> None:
        self._counters: Counter[tuple[str, str, str]] = Counter()
        self._gauges: dict[tuple[str, str], float] = {}
        self._durations: dict[tuple[str, str], list[float]] = defaultdict(list)
        self._lock = Lock()

    def increment(self, name: str, *, agent_id: str = "runtime", capability: str = "") -> None:
        with self._lock:
            self._counters[(name, agent_id, capability)] += 1

    def gauge(self, name: str, value: float, *, agent_id: str = "runtime") -> None:
        with self._lock:
            self._gauges[(name, agent_id)] = value

    def duration(self, name: str, value: float, *, agent_id: str) -> None:
        with self._lock:
            values = self._durations[(name, agent_id)]
            values.append(value)
            del values[:-100]

    def safe_snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": {
                    f"{name}:{agent_id}:{capability}": value
                    for (name, agent_id, capability), value in self._counters.items()
                },
                "gauges": {
                    f"{name}:{agent_id}": value
                    for (name, agent_id), value in self._gauges.items()
                },
            }


agent_runtime_metrics = AgentRuntimeMetrics()

