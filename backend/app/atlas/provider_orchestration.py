"""Explicit, bounded provider execution before deterministic Atlas compilation."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from threading import Lock
from time import perf_counter
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.atlas.canonical import AtlasCanonicalModel, FrozenJson, canonical_json, fingerprint
from app.atlas.compiler import AtlasCompilationResult
from app.atlas.compiler_contracts import (
    AtlasAccessSnapshot,
    AtlasCompilationSnapshot,
    AtlasCompilerPolicy,
    AtlasContextRequest,
    AtlasProviderInputSnapshot,
    AtlasProviderSelectionEntry,
    AtlasProviderSelectionPlan,
    AtlasProvenance,
)
from app.atlas.constants import (
    ATLAS_COMPILER_CONTRACT_VERSION,
    ATLAS_CONTEXT_PACKAGE_VERSION,
    ATLAS_MANIFEST_VERSION,
)
from app.atlas.errors import AtlasErrorCategory
from app.atlas.models import (
    AtlasProviderBudget,
    AtlasProviderCollectionContext,
    AtlasProviderLifecycleState,
    AtlasProviderRequest,
    AtlasProviderResult,
    validate_safe_json_keys,
)
from app.atlas.registry import AtlasProviderRegistry, contract_compatible


def _freeze(value) -> FrozenJson:
    frozen = value if isinstance(value, FrozenJson) else FrozenJson(value)
    validate_safe_json_keys(frozen.to_python())
    return frozen


class AtlasProviderFailurePolicy(AtlasCanonicalModel):
    fail_on_required_provider_error: bool = True
    allow_partial_optional_results: bool = True
    include_failed_provider_snapshots: bool = False
    maximum_failed_optional_providers: int = Field(default=32, ge=0, le=32)
    maximum_provider_warnings: int = Field(default=64, ge=0, le=256)


class AtlasProviderExecutionPlan(AtlasCanonicalModel):
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    required: bool = False
    priority_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)
    capabilities: tuple[str, ...] = ()
    provider_config: FrozenJson = Field(default_factory=FrozenJson)
    expected_contract_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")

    _config = field_validator("provider_config", mode="before")(_freeze)

    @field_validator("capabilities")
    @classmethod
    def canonical_capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("Provider capabilities must be unique.")
        return tuple(sorted(value))


class AtlasProviderExecutionRequest(AtlasCanonicalModel):
    request_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    compilation_time: datetime
    compiler_contract_version: str = ATLAS_COMPILER_CONTRACT_VERSION
    package_contract_version: str = ATLAS_CONTEXT_PACKAGE_VERSION
    manifest_contract_version: str = ATLAS_MANIFEST_VERSION
    selected_provider_plans: tuple[AtlasProviderExecutionPlan, ...]
    intent: str = Field(min_length=1, max_length=128)
    capabilities: tuple[str, ...] = ()
    compiler_policy: AtlasCompilerPolicy = Field(default_factory=AtlasCompilerPolicy)
    failure_policy: AtlasProviderFailurePolicy = Field(default_factory=AtlasProviderFailurePolicy)
    access_snapshot: AtlasAccessSnapshot | None = None
    source_configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    caller_metadata: FrozenJson = Field(default_factory=FrozenJson)

    _metadata = field_validator("caller_metadata", mode="before")(_freeze)

    @field_validator("capabilities")
    @classmethod
    def canonical_capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("Capabilities must be unique.")
        return tuple(sorted(value))

    @field_validator("selected_provider_plans", mode="before")
    @classmethod
    def canonical_plans(cls, value):
        plans = tuple(value)
        ids = [item.provider_id if isinstance(item, AtlasProviderExecutionPlan) else item["provider_id"] for item in plans]
        if len(ids) != len(set(ids)):
            raise ValueError("Provider execution plans must be unique.")
        return tuple(sorted(plans, key=lambda item: item.provider_id if isinstance(item, AtlasProviderExecutionPlan) else item["provider_id"]))

    @model_validator(mode="after")
    def compatible_versions(self):
        if (
            self.compiler_contract_version != ATLAS_COMPILER_CONTRACT_VERSION
            or self.package_contract_version != ATLAS_CONTEXT_PACKAGE_VERSION
            or self.manifest_contract_version != ATLAS_MANIFEST_VERSION
        ):
            raise ValueError("Atlas orchestration contract versions are incompatible.")
        return self


class AtlasProviderOperationalStatus(AtlasCanonicalModel):
    provider_id: str
    status: Literal["success", "partial", "unavailable", "failed", "timeout", "skipped"]
    safe_error_category: str | None = None
    duration_ms: float = Field(default=0.0, ge=0)


class AtlasValidatedProviderResult(AtlasCanonicalModel):
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    provider_contract_version: str = Field(pattern=r"^\d+\.\d+$")
    result_schema_version: str = Field(pattern=r"^\d+\.\d+$")
    status: Literal["success", "partial", "unavailable", "failed", "timeout", "skipped"]
    records: tuple[FrozenJson, ...] = Field(default=(), max_length=256)
    relation_candidates: tuple[FrozenJson, ...] = Field(default=(), max_length=256)
    warnings: tuple[str, ...] = Field(default=(), max_length=64)
    source_metadata: FrozenJson = Field(default_factory=FrozenJson)
    classification: Literal["internal", "confidential", "restricted"] = "internal"

    _records = field_validator("records", "relation_candidates", mode="before")(
        lambda value: tuple(_freeze(item) for item in value)
    )
    _metadata = field_validator("source_metadata", mode="before")(_freeze)

    @model_validator(mode="after")
    def unique_records(self):
        ids = []
        for item in self.records:
            value = item.to_python()
            if isinstance(value, dict) and "id" in value:
                ids.append(str(value["id"]))
        if len(ids) != len(set(ids)):
            raise ValueError("Provider record identifiers must be unique.")
        return self

    @property
    def provider_result_fingerprint(self) -> str:
        return self.deterministic_fingerprint()


class AtlasProviderExecutionOutcome(AtlasCanonicalModel):
    execution_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    compilation_snapshot: AtlasCompilationSnapshot | None = None
    compilation_result: AtlasCompilationResult | None = None
    provider_operational_statuses: tuple[AtlasProviderOperationalStatus, ...] = ()
    safe_error_category: str | None = None


class AtlasOrchestrationMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.attempts = self.successes = self.failures = 0
        self.active = self.peak_active = self.provider_calls = 0
        self.provider_successes = self.provider_partials = 0
        self.provider_failures = self.provider_timeouts = self.provider_unavailable = 0
        self.last_status = "never"; self.last_error_category = None
        self.last_duration_ms = 0.0; self.last_provider_count = 0
        self.last_successful_provider_count = 0; self.last_failed_provider_count = 0
        self.last_snapshot_bytes = 0; self.last_compilation_success = False

    def begin(self, provider_count: int) -> None:
        with self._lock:
            self.attempts += 1; self.active += 1; self.peak_active = max(self.peak_active, self.active)
            self.last_provider_count = provider_count

    def finish(self, *, statuses, duration_ms: float, snapshot, compilation_success: bool, error: str | None) -> None:
        with self._lock:
            self.active = max(self.active - 1, 0)
            self.provider_calls += len([item for item in statuses if item.status != "skipped"])
            self.provider_successes += sum(item.status == "success" for item in statuses)
            self.provider_partials += sum(item.status == "partial" for item in statuses)
            self.provider_timeouts += sum(item.status == "timeout" for item in statuses)
            self.provider_unavailable += sum(item.status == "unavailable" for item in statuses)
            failed = sum(item.status in {"failed", "timeout", "unavailable"} for item in statuses)
            self.provider_failures += failed
            self.last_successful_provider_count = sum(item.status in {"success", "partial"} for item in statuses)
            self.last_failed_provider_count = failed
            self.last_duration_ms = round(max(duration_ms, 0.0), 3)
            self.last_snapshot_bytes = len(snapshot.canonical_bytes()) if snapshot else 0
            self.last_compilation_success = compilation_success
            self.last_error_category = error
            self.last_status = "success" if compilation_success else "failure"
            if compilation_success: self.successes += 1
            else: self.failures += 1

    def safe_snapshot(self) -> dict[str, object]:
        with self._lock:
            return {key: value for key, value in self.__dict__.items() if key != "_lock"}


class AtlasProviderOrchestrator:
    def __init__(self, registry: AtlasProviderRegistry, compile_context: Callable[[AtlasCompilationSnapshot], AtlasCompilationResult], *, state_provider: Callable[[str], AtlasProviderLifecycleState] | None = None, concurrency_limit: int = 4) -> None:
        self.registry = registry; self._compile_context = compile_context; self._state_provider = state_provider
        self.concurrency_limit = max(int(concurrency_limit), 1)
        self.metrics = AtlasOrchestrationMetrics()

    async def execute(self, request: AtlasProviderExecutionRequest) -> AtlasProviderExecutionOutcome:
        started = perf_counter(); self.metrics.begin(len(request.selected_provider_plans)); statuses = (); snapshot = None
        try:
            semaphore = asyncio.Semaphore(self.concurrency_limit)
            results = await asyncio.gather(*(self._execute_plan(request, plan, semaphore) for plan in request.selected_provider_plans))
            statuses = tuple(item[0] for item in results)
            required_failure = any(plan.required and status.status not in {"success", "partial"} for plan, (status, _) in zip(request.selected_provider_plans, results))
            if required_failure and request.failure_policy.fail_on_required_provider_error:
                error = AtlasErrorCategory.PROVIDER_ORCHESTRATION_REQUIRED_FAILED.value
                return self._failed(request, statuses, started, error)
            optional_failures = sum(
                not plan.required and status.status in {"failed", "timeout", "unavailable"}
                for plan, (status, _) in zip(request.selected_provider_plans, results)
            )
            if optional_failures > request.failure_policy.maximum_failed_optional_providers:
                return self._failed(request, statuses, started, AtlasErrorCategory.PROVIDER_ORCHESTRATION_FAILED.value)
            valid = [
                (plan, status, result)
                for plan, (status, result) in zip(request.selected_provider_plans, results)
                if result is not None
                and (
                    status.status == "success"
                    or (
                        status.status == "partial"
                        and (plan.required or request.failure_policy.allow_partial_optional_results)
                    )
                )
            ]
            snapshot = self._build_snapshot(request, valid, statuses)
            compiled = self._compile_context(snapshot)
            outcome = AtlasProviderExecutionOutcome(execution_request_fingerprint=request.deterministic_fingerprint(), compilation_snapshot=snapshot, compilation_result=compiled, provider_operational_statuses=statuses)
            self.metrics.finish(statuses=statuses, duration_ms=(perf_counter()-started)*1000, snapshot=snapshot, compilation_success=True, error=None)
            return outcome
        except Exception:
            error = AtlasErrorCategory.PROVIDER_ORCHESTRATION_FAILED.value
            return self._failed(request, statuses, started, error, snapshot)

    def _failed(self, request, statuses, started, error, snapshot=None):
        self.metrics.finish(statuses=statuses, duration_ms=(perf_counter()-started)*1000, snapshot=snapshot, compilation_success=False, error=error)
        return AtlasProviderExecutionOutcome(execution_request_fingerprint=request.deterministic_fingerprint(), provider_operational_statuses=statuses, safe_error_category=error)

    async def _execute_plan(self, request, plan, semaphore):
        started = perf_counter()
        if plan.provider_id not in self.registry:
            return AtlasProviderOperationalStatus(provider_id=plan.provider_id, status="unavailable", safe_error_category=AtlasErrorCategory.PROVIDER_INVALID_DEFINITION.value), None
        provider = self.registry.get(plan.provider_id)
        definition = provider.definition
        if not contract_compatible(plan.expected_contract_version, definition.contract_version) or not set(plan.capabilities).issubset(definition.capabilities):
            return AtlasProviderOperationalStatus(provider_id=plan.provider_id, status="failed", safe_error_category=AtlasErrorCategory.PROVIDER_CONTRACT_MISMATCH.value), None
        if self._state_provider and self._state_provider(plan.provider_id) not in {AtlasProviderLifecycleState.READY, AtlasProviderLifecycleState.DEGRADED}:
            return AtlasProviderOperationalStatus(provider_id=plan.provider_id, status="unavailable", safe_error_category=AtlasErrorCategory.PROVIDER_NOT_READY.value), None
        try:
            async with semaphore:
                provider_request = AtlasProviderRequest(request_id=request.request_id)
                context = AtlasProviderCollectionContext(provider_id=plan.provider_id, budget=AtlasProviderBudget(max_duration_seconds=plan.timeout_ms / 1000))
                async with asyncio.timeout(plan.timeout_ms / 1000):
                    result = AtlasProviderResult.model_validate(await provider.collect(provider_request, context))
            if result.provider_id != plan.provider_id or result.output_schema_version != definition.output_schema_version:
                raise ValueError("provider result mismatch")
            validated = self._validate_result(result, definition.contract_version)
            if len(validated.warnings) > request.failure_policy.maximum_provider_warnings:
                raise ValueError("Provider warning limit exceeded.")
            status = validated.status
            return AtlasProviderOperationalStatus(provider_id=plan.provider_id, status=status, duration_ms=round((perf_counter()-started)*1000, 3)), validated
        except TimeoutError:
            return AtlasProviderOperationalStatus(provider_id=plan.provider_id, status="timeout", safe_error_category=AtlasErrorCategory.PROVIDER_TIMEOUT.value, duration_ms=round((perf_counter()-started)*1000, 3)), None
        except Exception:
            return AtlasProviderOperationalStatus(provider_id=plan.provider_id, status="failed", safe_error_category=AtlasErrorCategory.PROVIDER_INPUT_INVALID.value, duration_ms=round((perf_counter()-started)*1000, 3)), None

    def _build_snapshot(self, request, valid, statuses):
        inputs = []
        selected = {plan.provider_id for plan, _, _ in valid}
        status_by_id = {item.provider_id: item for item in statuses}
        for sequence, (plan, _status, result) in enumerate(valid):
            provider = self.registry.get(plan.provider_id)
            records = tuple(item.to_python() for item in result.records + result.relation_candidates)
            digest = result.provider_result_fingerprint
            provenance = AtlasProvenance(provider_id=plan.provider_id, source_id=f"source-{plan.provider_id}", source_type="provider_result", source_version=result.result_schema_version, source_sequence=sequence, collected_at=request.compilation_time, original_reference=f"provider:{plan.provider_id}", transformation_steps=("provider_collection",), classification=result.classification, content_digest=digest)
            inputs.append(AtlasProviderInputSnapshot(provider_id=plan.provider_id, provider_version=provider.definition.version, provider_contract_version=provider.definition.contract_version, result_schema_version=result.result_schema_version, status=result.status if result.status in {"success", "partial", "unavailable"} else "unavailable", source_sequence=sequence, collected_at=request.compilation_time, capabilities=plan.capabilities, records=records, warnings=tuple(f"provider_warning_{index}" for index, _ in enumerate(result.warnings)), provenance=provenance, classification=result.classification, metadata=result.source_metadata))
        entries = tuple(AtlasProviderSelectionEntry(provider_id=plan.provider_id, selected=plan.provider_id in selected, required=plan.required, priority_points=plan.priority_points, requested_capabilities=plan.capabilities, matched_capabilities=plan.capabilities if plan.provider_id in selected else (), reason_categories=("provider_result_valid",) if plan.provider_id in selected else (f"provider_{status_by_id[plan.provider_id].status}",), exclusion_reason_category=None if plan.provider_id in selected else f"provider_{status_by_id[plan.provider_id].status}", ordinal=index) for index, plan in enumerate(request.selected_provider_plans))
        return AtlasCompilationSnapshot(request=AtlasContextRequest(request_id=request.request_id, intent=request.intent, requested_capabilities=request.capabilities, required_provider_ids=tuple(plan.provider_id for plan in request.selected_provider_plans if plan.required), optional_provider_ids=tuple(plan.provider_id for plan in request.selected_provider_plans if not plan.required), metadata=request.caller_metadata), access_snapshot=request.access_snapshot, compiler_policy=request.compiler_policy, provider_selection_plan=AtlasProviderSelectionPlan(entries=entries), provider_inputs=tuple(inputs), compilation_time=request.compilation_time, source_configuration_fingerprint=request.source_configuration_fingerprint, metadata={"provider_plan_fingerprint": fingerprint(request.selected_provider_plans)})

    @staticmethod
    def _validate_result(result: AtlasProviderResult, provider_contract_version: str) -> AtlasValidatedProviderResult:
        data = result.data
        records = data.get("records", ())
        relations = data.get("relation_candidates", ())
        if not isinstance(records, (list, tuple)) or not isinstance(relations, (list, tuple)):
            raise ValueError("Provider records and relations must be bounded collections.")
        relation_values = []
        for item in relations:
            if not isinstance(item, dict):
                raise ValueError("Relation candidates must be objects.")
            relation_values.append({**item, "item_type": "relation_candidate"})
        return AtlasValidatedProviderResult(
            provider_id=result.provider_id,
            provider_contract_version=provider_contract_version,
            result_schema_version=result.output_schema_version,
            status=result.status,
            records=tuple(sorted(records, key=canonical_json)),
            relation_candidates=tuple(sorted(relation_values, key=canonical_json)),
            warnings=tuple(sorted(result.warnings)),
            source_metadata=data.get("metadata", {}),
            classification=data.get("classification", "internal"),
        )
