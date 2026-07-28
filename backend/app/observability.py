from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock
from time import perf_counter

from pydantic import Field

from app.atlas.canonical import AtlasCanonicalModel
from app.core.config import settings


OBSERVABILITY_VERSION = "1.0"
LATENCY_BUCKETS = ("lt_5ms", "5_10ms", "10_25ms", "25_50ms", "50_100ms", "100ms_plus")


class AtlasHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    WARNING = "warning"
    FAILED = "failed"


class AtlasOperationalEvent(AtlasCanonicalModel):
    timestamp: datetime
    kind: str
    latency_ms: float = Field(default=0.0, ge=0)
    success: bool = True
    timeout: bool = False
    production_bytes: int = Field(default=0, ge=0)
    atlas_bytes: int = Field(default=0, ge=0)
    total_bytes: int = Field(default=0, ge=0)
    estimated_tokens: int = Field(default=0, ge=0)
    retained_nodes: int = Field(default=0, ge=0)
    dropped_nodes: int = Field(default=0, ge=0)


class AtlasCompilationSummary(AtlasCanonicalModel):
    compilation_count: int
    compilation_success: int
    compilation_failures: int
    average_compilation_ms: float
    p95_compilation_ms: float
    max_compilation_ms: float


class AtlasProviderSummary(AtlasCanonicalModel):
    provider_executions: int
    provider_failures: int
    provider_timeout_count: int
    average_provider_latency_ms: float
    provider_success_rate: float


class AtlasForgeSummary(AtlasCanonicalModel):
    adaptation_count: int
    adaptation_failures: int
    average_adaptation_latency_ms: float


class AtlasPromptSummary(AtlasCanonicalModel):
    production_prompt_bytes: float
    atlas_bytes: float
    total_bytes: float
    estimated_prompt_tokens: float
    retained_nodes: float
    dropped_nodes: float


class AtlasLatencySummary(AtlasCanonicalModel):
    histogram: dict[str, int]
    compile_moving_average_1m: float
    compile_moving_average_5m: float
    compile_moving_average_15m: float
    provider_moving_average_1m: float
    provider_moving_average_5m: float
    provider_moving_average_15m: float
    atlas_moving_average_1m: float
    atlas_moving_average_5m: float
    atlas_moving_average_15m: float
    request_rate_1m: float
    request_rate_5m: float
    request_rate_15m: float


class AtlasRequestSummary(AtlasCanonicalModel):
    total_requests: int
    shadow_requests: int
    canary_requests: int
    live_requests: int
    production_requests: int


class AtlasFallbackSummary(AtlasCanonicalModel):
    rollback_count: int
    emergency_disables: int
    atlas_bypasses: int
    fallback_count: int


class AtlasCapacitySummary(AtlasCanonicalModel):
    requests_per_hour: float
    peak_concurrency: int
    average_package_size: float
    average_forge_size: float
    average_retained_nodes: float
    average_dropped_nodes: float
    atlas_utilization: float


class AtlasOperationalSnapshot(AtlasCanonicalModel):
    version: str = OBSERVABILITY_VERSION
    timestamp: datetime
    health: AtlasHealthStatus
    alerts: tuple[str, ...]
    compilation_summary: AtlasCompilationSummary
    provider_summary: AtlasProviderSummary
    forge_summary: AtlasForgeSummary
    prompt_summary: AtlasPromptSummary
    latency_summary: AtlasLatencySummary
    request_summary: AtlasRequestSummary
    fallback_summary: AtlasFallbackSummary
    capacity_summary: AtlasCapacitySummary


class AtlasObservabilityService:
    def __init__(self) -> None:
        self._lock = Lock()
        self.recent_latency: deque[AtlasOperationalEvent] = deque(maxlen=1000)
        self.recent_compilations: deque[AtlasOperationalEvent] = deque(maxlen=500)
        self.recent_provider_executions: deque[AtlasOperationalEvent] = deque(maxlen=500)
        self.recent_prompt_sizes: deque[AtlasOperationalEvent] = deque(maxlen=500)
        self.total_requests = 0
        self.shadow_requests = 0
        self.canary_requests = 0
        self.live_requests = 0
        self.production_requests = 0
        self.rollback_count = 0
        self.emergency_disables = 0
        self.atlas_bypasses = 0
        self.fallback_count = 0
        self.active_requests = 0
        self.peak_concurrency = 0

    def record_decision(self, decision) -> None:
        with self._lock:
            self.total_requests += 1
            self.active_requests += 1
            self.peak_concurrency = max(self.peak_concurrency, self.active_requests)
            if decision.action.value == "shadow_only":
                self.shadow_requests += 1
            elif decision.action.value == "atlas_active":
                self.canary_requests += 1
            elif decision.action.value == "live_active":
                self.live_requests += 1
            else:
                self.production_requests += 1
            if decision.rollback_active:
                self.rollback_count += 1
                if decision.feature_source == "emergency_disable":
                    self.emergency_disables += 1
            if decision.fallback_reason is not None:
                self.fallback_count += 1
            if not decision.atlas_active:
                self.atlas_bypasses += 1

    def finish_request(self) -> None:
        with self._lock:
            self.active_requests = max(self.active_requests - 1, 0)

    def record_trace(self, trace) -> None:
        now = _now()
        with self._lock:
            provider = AtlasOperationalEvent(
                timestamp=now,
                kind="provider",
                latency_ms=trace.timing_summary.provider_orchestration_ms,
                success=trace.provider_summary.failed == 0 and trace.provider_summary.timeouts == 0,
                timeout=trace.provider_summary.timeouts > 0,
            )
            compile_event = AtlasOperationalEvent(
                timestamp=now,
                kind="compile",
                latency_ms=trace.timing_summary.compiler_ms,
                success=True,
            )
            forge = AtlasOperationalEvent(
                timestamp=now,
                kind="forge",
                latency_ms=trace.timing_summary.adapter_ms,
                success=True,
            )
            atlas = AtlasOperationalEvent(
                timestamp=now,
                kind="atlas",
                latency_ms=trace.timing_summary.total_ms,
                success=True,
            )
            prompt = AtlasOperationalEvent(
                timestamp=now,
                kind="prompt",
                production_bytes=trace.comparison_summary.production_prompt_bytes,
                atlas_bytes=trace.comparison_summary.atlas_context_bytes,
                total_bytes=trace.comparison_summary.shadow_prompt_bytes,
                estimated_tokens=trace.comparison_summary.shadow_prompt_tokens,
                retained_nodes=trace.node_summary.retained_nodes,
                dropped_nodes=trace.node_summary.dropped_nodes,
            )
            self.recent_provider_executions.append(provider)
            self.recent_compilations.append(compile_event)
            self.recent_latency.extend((provider, compile_event, forge, atlas))
            self.recent_prompt_sizes.append(prompt)

    def snapshot(self) -> AtlasOperationalSnapshot:
        with self._lock:
            return self._snapshot_locked(_now())

    def diagnostics(self) -> dict[str, object]:
        snapshot = self.snapshot()
        return {
            "atlas_health": snapshot.health.value,
            "compilation_rate": snapshot.compilation_summary.compilation_count,
            "average_compile_ms": snapshot.compilation_summary.average_compilation_ms,
            "average_forge_ms": snapshot.forge_summary.average_adaptation_latency_ms,
            "provider_success_rate": snapshot.provider_summary.provider_success_rate,
            "provider_failures": snapshot.provider_summary.provider_failures,
            "average_size_bytes": snapshot.prompt_summary.total_bytes,
            "average_atlas_size_bytes": snapshot.prompt_summary.atlas_bytes,
            "retained_nodes": snapshot.prompt_summary.retained_nodes,
            "dropped_nodes": snapshot.prompt_summary.dropped_nodes,
            "alerts": list(snapshot.alerts),
            "capacity": snapshot.capacity_summary.canonical_dict(),
        }

    def _snapshot_locked(self, now: datetime) -> AtlasOperationalSnapshot:
        compilation = self._compilation_summary()
        provider = self._provider_summary()
        forge = self._forge_summary()
        prompt = self._prompt_summary()
        latency = self._latency_summary(now)
        requests = AtlasRequestSummary(
            total_requests=self.total_requests,
            shadow_requests=self.shadow_requests,
            canary_requests=self.canary_requests,
            live_requests=self.live_requests,
            production_requests=self.production_requests,
        )
        fallback = AtlasFallbackSummary(
            rollback_count=self.rollback_count,
            emergency_disables=self.emergency_disables,
            atlas_bypasses=self.atlas_bypasses,
            fallback_count=self.fallback_count,
        )
        capacity = self._capacity_summary(now)
        alerts = self._alerts(compilation, provider, fallback)
        return AtlasOperationalSnapshot(
            timestamp=now,
            health=self._health(compilation, provider, latency, fallback),
            alerts=alerts,
            compilation_summary=compilation,
            provider_summary=provider,
            forge_summary=forge,
            prompt_summary=prompt,
            latency_summary=latency,
            request_summary=requests,
            fallback_summary=fallback,
            capacity_summary=capacity,
        )

    def _compilation_summary(self) -> AtlasCompilationSummary:
        items = tuple(self.recent_compilations)
        latencies = [item.latency_ms for item in items]
        failures = sum(not item.success for item in items)
        return AtlasCompilationSummary(
            compilation_count=len(items),
            compilation_success=len(items) - failures,
            compilation_failures=failures,
            average_compilation_ms=_average(latencies),
            p95_compilation_ms=_percentile(latencies, 95),
            max_compilation_ms=max(latencies, default=0.0),
        )

    def _provider_summary(self) -> AtlasProviderSummary:
        items = tuple(self.recent_provider_executions)
        failures = sum(not item.success for item in items)
        timeouts = sum(item.timeout for item in items)
        return AtlasProviderSummary(
            provider_executions=len(items),
            provider_failures=failures,
            provider_timeout_count=timeouts,
            average_provider_latency_ms=_average([item.latency_ms for item in items]),
            provider_success_rate=round(((len(items) - failures) / len(items)) * 100, 3) if items else 100.0,
        )

    def _forge_summary(self) -> AtlasForgeSummary:
        items = tuple(item for item in self.recent_latency if item.kind == "forge")
        failures = sum(not item.success for item in items)
        return AtlasForgeSummary(
            adaptation_count=len(items),
            adaptation_failures=failures,
            average_adaptation_latency_ms=_average([item.latency_ms for item in items]),
        )

    def _prompt_summary(self) -> AtlasPromptSummary:
        items = tuple(self.recent_prompt_sizes)
        return AtlasPromptSummary(
            production_prompt_bytes=_average([item.production_bytes for item in items]),
            atlas_bytes=_average([item.atlas_bytes for item in items]),
            total_bytes=_average([item.total_bytes for item in items]),
            estimated_prompt_tokens=_average([item.estimated_tokens for item in items]),
            retained_nodes=_average([item.retained_nodes for item in items]),
            dropped_nodes=_average([item.dropped_nodes for item in items]),
        )

    def _latency_summary(self, now: datetime) -> AtlasLatencySummary:
        return AtlasLatencySummary(
            histogram=self.latency_histogram(),
            compile_moving_average_1m=self._moving_average("compile", now, 60),
            compile_moving_average_5m=self._moving_average("compile", now, 300),
            compile_moving_average_15m=self._moving_average("compile", now, 900),
            provider_moving_average_1m=self._moving_average("provider", now, 60),
            provider_moving_average_5m=self._moving_average("provider", now, 300),
            provider_moving_average_15m=self._moving_average("provider", now, 900),
            atlas_moving_average_1m=self._moving_average("atlas", now, 60),
            atlas_moving_average_5m=self._moving_average("atlas", now, 300),
            atlas_moving_average_15m=self._moving_average("atlas", now, 900),
            request_rate_1m=self._request_rate(now, 60),
            request_rate_5m=self._request_rate(now, 300),
            request_rate_15m=self._request_rate(now, 900),
        )

    def latency_histogram(self) -> dict[str, int]:
        values = {bucket: 0 for bucket in LATENCY_BUCKETS}
        for event in self.recent_latency:
            values[_bucket(event.latency_ms)] += 1
        return values

    def _moving_average(self, kind: str, now: datetime, seconds: int) -> float:
        cutoff = now.timestamp() - seconds
        values = [
            event.latency_ms
            for event in self.recent_latency
            if event.kind == kind and event.timestamp.timestamp() >= cutoff
        ]
        return _average(values)

    def _request_rate(self, now: datetime, seconds: int) -> float:
        cutoff = now.timestamp() - seconds
        count = sum(event.kind == "atlas" and event.timestamp.timestamp() >= cutoff for event in self.recent_latency)
        return round(count / (seconds / 60), 3)

    def _capacity_summary(self, now: datetime) -> AtlasCapacitySummary:
        oldest = min((event.timestamp for event in self.recent_latency), default=now)
        elapsed_hours = max((now - oldest).total_seconds() / 3600, 1 / 3600)
        prompt = self._prompt_summary()
        atlas_requests = self.canary_requests + self.live_requests
        utilization = (atlas_requests / self.total_requests) * 100 if self.total_requests else 0.0
        return AtlasCapacitySummary(
            requests_per_hour=round(self.total_requests / elapsed_hours, 3),
            peak_concurrency=self.peak_concurrency,
            average_package_size=prompt.atlas_bytes,
            average_forge_size=prompt.total_bytes,
            average_retained_nodes=prompt.retained_nodes,
            average_dropped_nodes=prompt.dropped_nodes,
            atlas_utilization=round(utilization, 3),
        )

    def _alerts(
        self,
        compilation: AtlasCompilationSummary,
        provider: AtlasProviderSummary,
        fallback: AtlasFallbackSummary,
    ) -> tuple[str, ...]:
        alerts: list[str] = []
        if provider.provider_executions and provider.provider_timeout_count / provider.provider_executions > 0.10:
            alerts.append("provider_timeout_rate_high")
        if compilation.compilation_count and compilation.compilation_failures / compilation.compilation_count > 0.05:
            alerts.append("compilation_failure_rate_high")
        if compilation.average_compilation_ms > 100:
            alerts.append("average_compile_latency_high")
        if fallback.rollback_count:
            alerts.append("rollback_active")
        if settings.ctv_one_atlas_canary_emergency_disabled:
            alerts.append("emergency_disable_active")
        return tuple(sorted(alerts))

    def _health(
        self,
        compilation: AtlasCompilationSummary,
        provider: AtlasProviderSummary,
        latency: AtlasLatencySummary,
        fallback: AtlasFallbackSummary,
    ) -> AtlasHealthStatus:
        alerts = self._alerts(compilation, provider, fallback)
        if "emergency_disable_active" in alerts or "compilation_failure_rate_high" in alerts:
            return AtlasHealthStatus.FAILED
        if "provider_timeout_rate_high" in alerts or fallback.rollback_count:
            return AtlasHealthStatus.DEGRADED
        if latency.atlas_moving_average_1m > 100 or alerts:
            return AtlasHealthStatus.WARNING
        return AtlasHealthStatus.HEALTHY


atlas_observability_service = AtlasObservabilityService()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bucket(value: float) -> str:
    if value < 5:
        return "lt_5ms"
    if value < 10:
        return "5_10ms"
    if value < 25:
        return "10_25ms"
    if value < 50:
        return "25_50ms"
    if value < 100:
        return "50_100ms"
    return "100ms_plus"


def _average(values) -> float:
    items = list(values)
    return round(sum(items) / len(items), 3) if items else 0.0


def _percentile(values, percentile: int) -> float:
    items = sorted(values)
    if not items:
        return 0.0
    index = min(round((percentile / 100) * (len(items) - 1)), len(items) - 1)
    return round(items[index], 3)
