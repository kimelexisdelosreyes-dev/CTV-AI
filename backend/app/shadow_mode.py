from __future__ import annotations

import hashlib
from collections import deque
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock
from time import perf_counter
from typing import TYPE_CHECKING, Any

from pydantic import Field

from app.atlas.canonical import AtlasCanonicalModel, canonical_json, fingerprint
from app.atlas.models import AtlasRuntimeState
from app.atlas.compiler_contracts import AtlasManifestReference
from app.atlas.provider_orchestration import AtlasProviderExecutionPlan, AtlasProviderExecutionRequest
from app.core.config import settings
from app.forge.context_adapter import ForgeContextAdapter, ForgeContextWindow, estimate_text_tokens
from app.forge.prompt_builder import integrate_atlas_context, render_atlas_context
from app.observability import atlas_observability_service

if TYPE_CHECKING:
    from app.atlas.runtime_manager import AtlasRuntimeManager


SHADOW_TRACE_RING_CAPACITY = 100
EMPTY_SOURCE_CONFIGURATION_FINGERPRINT = hashlib.sha256(b"atlas-shadow-empty-provider-plan").hexdigest()
SHADOW_DETERMINISTIC_COMPILATION_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class AtlasTraceProviderSummary(AtlasCanonicalModel):
    registered_providers: int
    selected_providers: int
    successful: int
    partial: int
    failed: int
    timeouts: int


class AtlasTraceNodeSummary(AtlasCanonicalModel):
    compiled_nodes: int
    retained_nodes: int
    dropped_nodes: int
    highest_score: int | None = None
    lowest_score: int | None = None


class AtlasTraceTokenSummary(AtlasCanonicalModel):
    estimated_package_tokens: int
    estimated_forge_tokens: int
    budget: int
    retained: int
    dropped: int


class AtlasTraceTimingSummary(AtlasCanonicalModel):
    provider_orchestration_ms: float = Field(ge=0)
    compiler_ms: float = Field(ge=0)
    adapter_ms: float = Field(ge=0)
    comparison_ms: float = Field(ge=0)
    trace_ms: float = Field(ge=0)
    total_ms: float = Field(ge=0)


class AtlasTraceLifecycleSummary(AtlasCanonicalModel):
    runtime_state: str
    shadow_enabled: bool
    adapter_enabled: bool
    compiler_ready: bool


class AtlasTraceFeatureFlags(AtlasCanonicalModel):
    shadow_enabled: bool
    canary_enabled: bool
    live_enabled: bool
    canary_percentage: int


class AtlasTraceCanarySummary(AtlasCanonicalModel):
    policy_decision: str
    canary_eligible: bool
    feature_source: str
    fallback_reason: str | None = None
    atlas_active: bool
    live_active: bool
    atlas_injected: bool
    rollback_active: bool


class AtlasTraceComparisonSummary(AtlasCanonicalModel):
    production_prompt_bytes: int
    shadow_prompt_bytes: int
    delta_bytes: int
    production_prompt_tokens: int
    shadow_prompt_tokens: int
    delta_tokens: int
    production_section_count: int
    shadow_section_count: int
    atlas_addition_count: int
    atlas_context_bytes: int
    atlas_context_tokens: int


class AtlasTrace(AtlasCanonicalModel):
    trace_id: str
    request_id: str
    compilation_snapshot_fingerprint: str
    package_fingerprint: str
    manifest_reference: dict[str, Any]
    forge_context_fingerprint: str
    provider_summary: AtlasTraceProviderSummary
    node_summary: AtlasTraceNodeSummary
    token_summary: AtlasTraceTokenSummary
    timing_summary: AtlasTraceTimingSummary
    lifecycle_summary: AtlasTraceLifecycleSummary
    feature_flags: AtlasTraceFeatureFlags
    canary_summary: AtlasTraceCanarySummary
    comparison_summary: AtlasTraceComparisonSummary


class CanaryDecisionAction(StrEnum):
    ATLAS_ACTIVE = "atlas_active"
    SHADOW_ONLY = "shadow_only"
    LIVE_ACTIVE = "live_active"
    PRODUCTION = "production"
    ROLLBACK = "rollback"


class CanaryPolicyDecision(AtlasCanonicalModel):
    user_identifier_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    action: CanaryDecisionAction
    eligible: bool
    atlas_active: bool
    live_active: bool = False
    atlas_injected: bool = False
    rollback_active: bool
    feature_source: str
    fallback_reason: str | None = None
    canary_enabled: bool
    shadow_enabled: bool
    live_enabled: bool
    canary_percentage: int = Field(ge=0, le=100)


class CanaryPolicy:
    def __init__(
        self,
        *,
        canary_enabled: bool | None = None,
        shadow_enabled: bool | None = None,
        live_enabled: bool | None = None,
        canary_percentage: int | None = None,
        canary_users: str | tuple[str, ...] | None = None,
        emergency_disabled: bool | None = None,
    ) -> None:
        self.canary_enabled = settings.ctv_one_atlas_canary_enabled if canary_enabled is None else canary_enabled
        self.shadow_enabled = settings.ctv_one_atlas_shadow_enabled if shadow_enabled is None else shadow_enabled
        self.live_enabled = settings.ctv_one_atlas_live_enabled if live_enabled is None else live_enabled
        raw_percentage = (
            settings.ctv_one_atlas_canary_percentage if canary_percentage is None else canary_percentage
        )
        self.canary_percentage = min(max(int(raw_percentage), 0), 100)
        self.emergency_disabled = (
            settings.ctv_one_atlas_canary_emergency_disabled
            if emergency_disabled is None
            else emergency_disabled
        )
        self.allowlist = _parse_canary_users(
            settings.ctv_one_atlas_canary_users if canary_users is None else canary_users
        )

    def decide(self, user_identifier: str | None) -> CanaryPolicyDecision:
        user_hash = _hash_identifier(user_identifier)
        if self.emergency_disabled:
            return self._decision(
                user_hash,
                CanaryDecisionAction.ROLLBACK,
                feature_source="emergency_disable",
                fallback_reason="emergency_disabled",
                rollback_active=True,
            )
        if not self.canary_enabled:
            action = (
                CanaryDecisionAction.SHADOW_ONLY
                if self.shadow_enabled
                else CanaryDecisionAction.LIVE_ACTIVE
                if self.live_enabled
                else CanaryDecisionAction.PRODUCTION
            )
            return self._decision(
                user_hash,
                action,
                eligible=action == CanaryDecisionAction.LIVE_ACTIVE,
                atlas_active=action == CanaryDecisionAction.LIVE_ACTIVE,
                live_active=action == CanaryDecisionAction.LIVE_ACTIVE,
                atlas_injected=action == CanaryDecisionAction.LIVE_ACTIVE,
                feature_source=(
                    "shadow"
                    if action == CanaryDecisionAction.SHADOW_ONLY
                    else "live"
                    if action == CanaryDecisionAction.LIVE_ACTIVE
                    else "canary_disabled"
                ),
                fallback_reason=(
                    "shadow_enabled"
                    if action == CanaryDecisionAction.SHADOW_ONLY
                    else "canary_disabled"
                    if action == CanaryDecisionAction.PRODUCTION
                    else None
                ),
            )
        normalized = _normalize_identifier(user_identifier)
        if normalized and normalized in self.allowlist:
            return self._decision(
                user_hash,
                CanaryDecisionAction.ATLAS_ACTIVE,
                eligible=True,
                atlas_active=True,
                feature_source="allowlist",
            )
        if self._percentage_eligible(user_hash):
            return self._decision(
                user_hash,
                CanaryDecisionAction.ATLAS_ACTIVE,
                eligible=True,
                atlas_active=True,
                feature_source="percentage",
            )
        return self._decision(
            user_hash,
            CanaryDecisionAction.SHADOW_ONLY
            if self.shadow_enabled
            else CanaryDecisionAction.LIVE_ACTIVE
            if self.live_enabled
            else CanaryDecisionAction.PRODUCTION,
            eligible=self.live_enabled and not self.shadow_enabled,
            atlas_active=self.live_enabled and not self.shadow_enabled,
            live_active=self.live_enabled and not self.shadow_enabled,
            atlas_injected=self.live_enabled and not self.shadow_enabled,
            feature_source="live" if self.live_enabled and not self.shadow_enabled else "default_production",
            fallback_reason=None if self.live_enabled and not self.shadow_enabled else "not_eligible",
        )

    def _percentage_eligible(self, user_hash: str | None) -> bool:
        if self.canary_percentage <= 0 or user_hash is None:
            return False
        bucket = int(user_hash[:8], 16) % 100
        return bucket < self.canary_percentage

    def _decision(
        self,
        user_hash: str | None,
        action: CanaryDecisionAction,
        *,
        eligible: bool = False,
        atlas_active: bool = False,
        live_active: bool = False,
        atlas_injected: bool = False,
        rollback_active: bool = False,
        feature_source: str,
        fallback_reason: str | None = None,
    ) -> CanaryPolicyDecision:
        return CanaryPolicyDecision(
            user_identifier_hash=user_hash,
            action=action,
            eligible=eligible,
            atlas_active=atlas_active,
            live_active=live_active,
            atlas_injected=atlas_injected,
            rollback_active=rollback_active,
            feature_source=feature_source,
            fallback_reason=fallback_reason,
            canary_enabled=self.canary_enabled,
            shadow_enabled=self.shadow_enabled,
            live_enabled=self.live_enabled,
            canary_percentage=self.canary_percentage,
        )


class CanaryMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.eligible_requests = 0
        self.production_requests = 0
        self.atlas_requests = 0
        self.fallback_requests = 0
        self.policy_decisions = 0
        self.total_atlas_latency_ms = 0.0
        self.total_prompt_delta_bytes = 0
        self.total_retained_nodes = 0
        self.total_dropped_nodes = 0
        self.live_requests = 0
        self.live_context_bytes = 0
        self.live_context_tokens = 0
        self.atlas_injection_count = 0
        self.atlas_failures = 0

    def record_decision(self, decision: CanaryPolicyDecision) -> None:
        with self._lock:
            self.policy_decisions += 1
            if decision.eligible:
                self.eligible_requests += 1
            if decision.atlas_active:
                self.atlas_requests += 1
            else:
                self.production_requests += 1
            if decision.fallback_reason is not None:
                self.fallback_requests += 1
            if decision.live_active:
                self.live_requests += 1

    def record_trace(self, trace: "AtlasTrace") -> None:
        if not trace.canary_summary.atlas_active:
            return
        with self._lock:
            self.total_atlas_latency_ms += trace.timing_summary.total_ms
            self.total_prompt_delta_bytes += trace.comparison_summary.delta_bytes
            self.total_retained_nodes += trace.node_summary.retained_nodes
            self.total_dropped_nodes += trace.node_summary.dropped_nodes
            if trace.canary_summary.live_active:
                self.live_context_bytes += trace.comparison_summary.shadow_prompt_bytes
                self.live_context_tokens += trace.comparison_summary.shadow_prompt_tokens
            if trace.canary_summary.atlas_injected:
                self.atlas_injection_count += 1

    def record_atlas_failure(self, decision: CanaryPolicyDecision) -> None:
        if not decision.atlas_active:
            return
        with self._lock:
            self.atlas_failures += 1
            self.fallback_requests += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            divisor = max(self.atlas_requests, 1)
            return {
                "canary_enabled": settings.ctv_one_atlas_canary_enabled,
                "allowlist_size": len(_parse_canary_users(settings.ctv_one_atlas_canary_users)),
                "percentage_rollout": settings.ctv_one_atlas_canary_percentage,
                "eligible_requests": self.eligible_requests,
                "atlas_requests": self.atlas_requests,
                "fallback_requests": self.fallback_requests,
                "rollback_state": settings.ctv_one_atlas_canary_emergency_disabled,
                "live_enabled": settings.ctv_one_atlas_live_enabled,
                "live_requests": self.live_requests,
                "live_context_bytes": self.live_context_bytes,
                "live_context_tokens": self.live_context_tokens,
                "atlas_injections": self.atlas_injection_count,
                "atlas_failures": self.atlas_failures,
                "average_latency_ms": round(self.total_atlas_latency_ms / divisor, 3) if self.atlas_requests else 0.0,
                "average_delta_bytes": (
                    round(self.total_prompt_delta_bytes / divisor, 3) if self.atlas_requests else 0.0
                ),
                "average_retained_nodes": round(self.total_retained_nodes / divisor, 3) if self.atlas_requests else 0.0,
                "average_dropped_nodes": round(self.total_dropped_nodes / divisor, 3) if self.atlas_requests else 0.0,
            }


class AtlasShadowMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.requests = 0
        self.compilations = 0
        self.failures = 0
        self.traces = 0
        self.total_latency_ms = 0.0
        self.total_package_bytes = 0
        self.total_forge_bytes = 0

    def record_success(self, *, latency_ms: float, package_bytes: int, forge_bytes: int) -> None:
        with self._lock:
            self.requests += 1
            self.compilations += 1
            self.traces += 1
            self.total_latency_ms += latency_ms
            self.total_package_bytes += package_bytes
            self.total_forge_bytes += forge_bytes

    def record_failure(self) -> None:
        with self._lock:
            self.requests += 1
            self.failures += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            divisor = max(self.traces, 1)
            return {
                "shadow_enabled": settings.ctv_one_atlas_shadow_enabled,
                "shadow_requests": self.requests,
                "shadow_compilations": self.compilations,
                "shadow_failures": self.failures,
                "shadow_traces": self.traces,
                "average_shadow_latency_ms": round(self.total_latency_ms / divisor, 3) if self.traces else 0.0,
                "average_package_bytes": round(self.total_package_bytes / divisor, 3) if self.traces else 0.0,
                "average_forge_bytes": round(self.total_forge_bytes / divisor, 3) if self.traces else 0.0,
            }


class AtlasTraceRingBuffer:
    def __init__(self, capacity: int = SHADOW_TRACE_RING_CAPACITY) -> None:
        self.capacity = max(int(capacity), 1)
        self._items: deque[AtlasTrace] = deque(maxlen=self.capacity)
        self._lock = Lock()

    def append(self, trace: AtlasTrace) -> None:
        with self._lock:
            self._items.append(trace)

    def snapshot(self) -> tuple[AtlasTrace, ...]:
        with self._lock:
            return tuple(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class AtlasShadowModeService:
    def __init__(
        self,
        runtime_manager: "AtlasRuntimeManager",
        *,
        metrics: AtlasShadowMetrics | None = None,
        ring_buffer: AtlasTraceRingBuffer | None = None,
    ) -> None:
        self.runtime_manager = runtime_manager
        self.metrics = metrics or AtlasShadowMetrics()
        self.ring_buffer = ring_buffer or AtlasTraceRingBuffer()
        self.canary_metrics = CanaryMetrics()

    async def execute(
        self,
        *,
        production_prompt: str,
        request_id: str,
        intent: str = "chat",
        policy_decision: CanaryPolicyDecision | None = None,
    ) -> AtlasTrace | None:
        decision = policy_decision or CanaryPolicy().decide(None)
        if decision.rollback_active or (
            not settings.ctv_one_atlas_shadow_enabled and not decision.atlas_active
        ):
            return None
        total_started = perf_counter()
        try:
            request = AtlasProviderExecutionRequest(
                request_id=request_id,
                compilation_time=SHADOW_DETERMINISTIC_COMPILATION_TIME,
                selected_provider_plans=self._provider_plans(),
                intent=intent,
                capabilities=self._provider_capabilities(),
                source_configuration_fingerprint=EMPTY_SOURCE_CONFIGURATION_FINGERPRINT,
            )
            provider_started = perf_counter()
            outcome = await self.runtime_manager.execute_provider_plan(request)
            provider_ms = (perf_counter() - provider_started) * 1000
            result = outcome.compilation_result
            snapshot = outcome.compilation_snapshot
            if result is None or snapshot is None:
                raise RuntimeError(outcome.safe_error_category or "atlas_shadow_compilation_failed")

            adapter_started = perf_counter()
            adapter = ForgeContextAdapter(atlas_enabled=True, adapter_enabled=True)
            window = adapter.adapt(result.context_package)
            adapter_ms = (perf_counter() - adapter_started) * 1000

            comparison_started = perf_counter()
            comparison = compare_prompts(production_prompt, window)
            comparison_ms = (perf_counter() - comparison_started) * 1000

            trace_started = perf_counter()
            trace = build_trace(
                runtime_manager=self.runtime_manager,
                request_id=request_id,
                snapshot_fingerprint=snapshot.snapshot_fingerprint,
                window=window,
                provider_statuses=outcome.provider_operational_statuses,
                comparison=comparison,
                provider_orchestration_ms=provider_ms,
                adapter_ms=adapter_ms,
                comparison_ms=comparison_ms,
                trace_ms=0.0,
                total_ms=(perf_counter() - total_started) * 1000,
                policy_decision=decision,
            )
            trace_ms = (perf_counter() - trace_started) * 1000
            trace = trace.model_copy(
                update={
                    "timing_summary": trace.timing_summary.model_copy(
                        update={
                            "trace_ms": round(trace_ms, 3),
                            "total_ms": round((perf_counter() - total_started) * 1000, 3),
                        }
                    )
                }
            )
            self.ring_buffer.append(trace)
            self.metrics.record_success(
                latency_ms=trace.timing_summary.total_ms,
                package_bytes=result.context_package.serialized_bytes(),
                forge_bytes=len(window.canonical_bytes()),
            )
            self.canary_metrics.record_trace(trace)
            return trace
        except Exception:
            self.metrics.record_failure()
            self.canary_metrics.record_atlas_failure(decision)
            return None

    def diagnostics(self) -> dict[str, object]:
        payload = self.metrics.snapshot()
        payload["canary"] = self.canary_metrics.snapshot()
        return payload

    def _provider_plans(self) -> tuple[AtlasProviderExecutionPlan, ...]:
        return tuple(
            AtlasProviderExecutionPlan(
                provider_id=definition.provider_id,
                required=definition.required,
                capabilities=tuple(sorted(definition.capabilities)),
                timeout_ms=int(definition.default_timeout_seconds * 1000),
                expected_contract_version=definition.contract_version,
            )
            for definition in self.runtime_manager.registry.definitions()
            if definition.enabled_by_default
        )

    def _provider_capabilities(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    capability
                    for definition in self.runtime_manager.registry.definitions()
                    if definition.enabled_by_default
                    for capability in definition.capabilities
                }
            )
        )

    async def route_messages(
        self,
        *,
        messages: list[dict[str, str]],
        request_id: str,
        user_identifier: str | None,
        intent: str = "chat",
    ) -> tuple[list[dict[str, str]], AtlasTrace | None, CanaryPolicyDecision]:
        production_prompt = production_prompt_from_messages(messages)
        decision = CanaryPolicy().decide(user_identifier)
        self.canary_metrics.record_decision(decision)
        atlas_observability_service.record_decision(decision)
        if decision.rollback_active:
            atlas_observability_service.finish_request()
            return messages, None, decision
        trace = await self.execute(
            production_prompt=production_prompt,
            request_id=request_id,
            intent=intent,
            policy_decision=decision,
        )
        if trace is not None:
            atlas_observability_service.record_trace(trace)
        atlas_observability_service.finish_request()
        if not decision.atlas_active or trace is None:
            return messages, trace, decision
        routed = atlas_messages(messages, trace)
        return routed, trace, decision


def production_prompt_from_messages(messages: list[dict[str, str]]) -> str:
    return canonical_json(tuple({"role": item.get("role", ""), "content": item.get("content", "")} for item in messages))


def shadow_request_id(production_prompt: str) -> str:
    return f"shadow-{hashlib.sha256(production_prompt.encode('utf-8')).hexdigest()[:24]}"


def atlas_messages(messages: list[dict[str, str]], trace: AtlasTrace) -> list[dict[str, str]]:
    system_content = next((item.get("content", "") for item in messages if item.get("role") == "system"), "")
    atlas_prompt = integrate_atlas_context(
        system_content,
        _window_reference(trace),
        atlas_enabled=True,
        forge_adapter_enabled=True,
    )
    filtered = [dict(item) for item in messages if item.get("role") != "system"]
    return [{"role": "system", "content": atlas_prompt}, *filtered]


def _window_reference(trace: AtlasTrace) -> ForgeContextWindow:
    return ForgeContextWindow(
        context_blocks=(),
        estimated_tokens=trace.token_summary.estimated_forge_tokens,
        dropped_node_count=trace.node_summary.dropped_nodes,
        retained_node_count=trace.node_summary.retained_nodes,
        package_fingerprint=trace.package_fingerprint,
        manifest_reference=AtlasManifestReference.model_validate(trace.manifest_reference),
        atlas_package_version="1.0",
    )


def compare_prompts(production_prompt: str, window: ForgeContextWindow) -> AtlasTraceComparisonSummary:
    shadow_prompt = integrate_atlas_context(
        production_prompt,
        window,
        atlas_enabled=True,
        forge_adapter_enabled=True,
    )
    atlas_context = render_atlas_context(window)
    production_bytes = len(production_prompt.encode("utf-8"))
    shadow_bytes = len(shadow_prompt.encode("utf-8"))
    production_tokens = estimate_text_tokens(production_prompt)
    shadow_tokens = estimate_text_tokens(shadow_prompt)
    return AtlasTraceComparisonSummary(
        production_prompt_bytes=production_bytes,
        shadow_prompt_bytes=shadow_bytes,
        delta_bytes=shadow_bytes - production_bytes,
        production_prompt_tokens=production_tokens,
        shadow_prompt_tokens=shadow_tokens,
        delta_tokens=shadow_tokens - production_tokens,
        production_section_count=_section_count(production_prompt),
        shadow_section_count=_section_count(shadow_prompt),
        atlas_addition_count=1 if "Atlas Context" in shadow_prompt and "Atlas Context" not in production_prompt else 0,
        atlas_context_bytes=len(atlas_context.encode("utf-8")),
        atlas_context_tokens=estimate_text_tokens(atlas_context),
    )


def build_trace(
    *,
    runtime_manager: "AtlasRuntimeManager",
    request_id: str,
    snapshot_fingerprint: str,
    window: ForgeContextWindow,
    provider_statuses,
    comparison: AtlasTraceComparisonSummary,
    provider_orchestration_ms: float,
    adapter_ms: float,
    comparison_ms: float,
    trace_ms: float,
    total_ms: float,
    policy_decision: CanaryPolicyDecision | None = None,
) -> AtlasTrace:
    scores = tuple(block.confidence for block in window.context_blocks)
    deterministic_seed = {
        "request_id": request_id,
        "snapshot": snapshot_fingerprint,
        "package": window.package_fingerprint,
        "forge": window.deterministic_fingerprint(),
            "comparison": comparison.canonical_dict(),
            "canary": (policy_decision.canonical_dict() if policy_decision else {}),
        }
    decision = policy_decision or CanaryPolicy().decide(None)
    return AtlasTrace(
        trace_id=f"trace-{fingerprint(deterministic_seed)[:32]}",
        request_id=request_id,
        compilation_snapshot_fingerprint=snapshot_fingerprint,
        package_fingerprint=window.package_fingerprint,
        manifest_reference=window.manifest_reference.canonical_dict(),
        forge_context_fingerprint=window.deterministic_fingerprint(),
        provider_summary=AtlasTraceProviderSummary(
            registered_providers=len(runtime_manager.records),
            selected_providers=len(provider_statuses),
            successful=sum(item.status == "success" for item in provider_statuses),
            partial=sum(item.status == "partial" for item in provider_statuses),
            failed=sum(item.status in {"failed", "unavailable"} for item in provider_statuses),
            timeouts=sum(item.status == "timeout" for item in provider_statuses),
        ),
        node_summary=AtlasTraceNodeSummary(
            compiled_nodes=window.retained_node_count + window.dropped_node_count,
            retained_nodes=window.retained_node_count,
            dropped_nodes=window.dropped_node_count,
            highest_score=max(scores) if scores else None,
            lowest_score=min(scores) if scores else None,
        ),
        token_summary=AtlasTraceTokenSummary(
            estimated_package_tokens=comparison.atlas_context_tokens,
            estimated_forge_tokens=window.estimated_tokens,
            budget=settings.ctv_one_forge_atlas_max_tokens,
            retained=window.retained_node_count,
            dropped=window.dropped_node_count,
        ),
        timing_summary=AtlasTraceTimingSummary(
            provider_orchestration_ms=round(provider_orchestration_ms, 3),
            compiler_ms=round(runtime_manager.compilation_metrics.last_compilation_duration_ms, 3),
            adapter_ms=round(adapter_ms, 3),
            comparison_ms=round(comparison_ms, 3),
            trace_ms=round(trace_ms, 3),
            total_ms=round(total_ms, 3),
        ),
        lifecycle_summary=AtlasTraceLifecycleSummary(
            runtime_state=runtime_manager.runtime_state.value,
            shadow_enabled=settings.ctv_one_atlas_shadow_enabled,
            adapter_enabled=True,
            compiler_ready=runtime_manager.runtime_state == AtlasRuntimeState.READY and runtime_manager.compiler is not None,
        ),
        feature_flags=AtlasTraceFeatureFlags(
            shadow_enabled=settings.ctv_one_atlas_shadow_enabled,
            canary_enabled=settings.ctv_one_atlas_canary_enabled,
            live_enabled=settings.ctv_one_atlas_live_enabled,
            canary_percentage=settings.ctv_one_atlas_canary_percentage,
        ),
        canary_summary=AtlasTraceCanarySummary(
            policy_decision=decision.action.value,
            canary_eligible=decision.eligible,
            feature_source=decision.feature_source,
            fallback_reason=decision.fallback_reason,
            atlas_active=decision.atlas_active,
            live_active=decision.live_active,
            atlas_injected=decision.atlas_injected,
            rollback_active=decision.rollback_active,
        ),
        comparison_summary=comparison,
    )


def _section_count(prompt: str) -> int:
    return sum(1 for section in prompt.split("\n\n") if section.strip())


def _parse_canary_users(value: str | tuple[str, ...]) -> frozenset[str]:
    if isinstance(value, str):
        raw = value.replace(";", ",").replace("\n", ",").split(",")
    else:
        raw = value
    return frozenset(item for item in (_normalize_identifier(item) for item in raw) if item)


def _normalize_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def _hash_identifier(value: str | None) -> str | None:
    normalized = _normalize_identifier(value)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
