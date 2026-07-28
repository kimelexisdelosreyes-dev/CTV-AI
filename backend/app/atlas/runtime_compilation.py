"""Thread-safe operational state for runtime-managed Atlas compilation."""
from __future__ import annotations

from threading import Lock


class AtlasCompilationOperationalMetrics:
    """Bounded scalar metrics kept outside deterministic compiler artifacts."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.compilation_attempts = 0
        self.compilation_successes = 0
        self.compilation_failures = 0
        self.active_compilations = 0
        self.peak_active_compilations = 0
        self.last_compilation_status = "never"
        self.last_error_category: str | None = None
        self.last_compilation_duration_ms = 0.0
        self.total_compilation_duration_ms = 0.0
        self.last_package_bytes = 0
        self.last_manifest_bytes = 0
        self.last_selected_node_count = 0
        self.last_conflict_count = 0

    def begin(self) -> None:
        with self._lock:
            self.compilation_attempts += 1
            self.active_compilations += 1
            self.peak_active_compilations = max(
                self.peak_active_compilations, self.active_compilations
            )

    def succeed(self, *, duration_ms: float, result) -> None:
        with self._lock:
            self.compilation_successes += 1
            self.last_compilation_status = "success"
            self.last_error_category = None
            self._record_duration(duration_ms)
            self.last_package_bytes = result.context_package.serialized_bytes()
            self.last_manifest_bytes = len(result.manifest.canonical_bytes())
            self.last_selected_node_count = len(result.graph_nodes)
            self.last_conflict_count = len(result.conflicts)

    def fail(self, *, duration_ms: float, error_category: str) -> None:
        with self._lock:
            self.compilation_failures += 1
            self.last_compilation_status = "failure"
            self.last_error_category = error_category[:80]
            self._record_duration(duration_ms)

    def finish(self) -> None:
        with self._lock:
            self.active_compilations = max(self.active_compilations - 1, 0)

    def _record_duration(self, duration_ms: float) -> None:
        value = max(float(duration_ms), 0.0)
        self.last_compilation_duration_ms = round(value, 3)
        self.total_compilation_duration_ms = round(
            self.total_compilation_duration_ms + value, 3
        )

    def active(self) -> int:
        with self._lock:
            return self.active_compilations

    def safe_snapshot(self) -> dict[str, object]:
        with self._lock:
            average = (
                self.total_compilation_duration_ms
                / max(self.compilation_successes + self.compilation_failures, 1)
            )
            return {
                "compilation_attempts": self.compilation_attempts,
                "compilation_successes": self.compilation_successes,
                "compilation_failures": self.compilation_failures,
                "active_compilations": self.active_compilations,
                "peak_active_compilations": self.peak_active_compilations,
                "last_compilation_status": self.last_compilation_status,
                "last_error_category": self.last_error_category,
                "last_compilation_duration_ms": self.last_compilation_duration_ms,
                "total_compilation_duration_ms": self.total_compilation_duration_ms,
                "average_compilation_duration_ms": round(average, 3),
                "last_package_bytes": self.last_package_bytes,
                "last_manifest_bytes": self.last_manifest_bytes,
                "last_selected_node_count": self.last_selected_node_count,
                "last_conflict_count": self.last_conflict_count,
            }
