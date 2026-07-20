from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from app.atlas.constants import ATLAS_PROVIDER_CONTRACT_VERSION


SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
CONTRACT_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")
STABLE_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
STABLE_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
PROHIBITED_CONTENT_KEY_FRAGMENTS = (
    "prompt",
    "reasoning",
    "exception",
    "traceback",
    "secret",
    "credential",
    "password",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_safe_json_keys(value: JsonValue) -> JsonValue:
    """Reject payload field names that could retain prompts, secrets, or traces."""
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            if any(fragment in normalized for fragment in PROHIBITED_CONTENT_KEY_FRAGMENTS):
                raise ValueError("Atlas payload contains a prohibited field name.")
            validate_safe_json_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            validate_safe_json_keys(nested)
    return value


class AtlasProviderLifecycleState(StrEnum):
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    DRAINING = "draining"
    STOPPED = "stopped"
    FAILED = "failed"


class AtlasRuntimeState(StrEnum):
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class AtlasHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class AtlasProviderBudget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_items: int = Field(default=16, ge=0, le=256)
    max_output_chars: int = Field(default=16_000, ge=1, le=128_000)
    max_duration_seconds: float = Field(default=30.0, gt=0, le=300)


class AtlasProviderDefinition(BaseModel):
    """Immutable, server-owned metadata for an approved Atlas provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    version: str = "1.0.0"
    contract_version: str = ATLAS_PROVIDER_CONTRACT_VERSION
    capabilities: frozenset[str] = frozenset()
    required_dependencies: frozenset[str] = frozenset()
    optional_dependencies: frozenset[str] = frozenset()
    required: bool = False
    enabled_by_default: bool = True
    supports_parallel_collection: bool = True
    supports_streaming: bool = False
    default_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    default_budget: AtlasProviderBudget = Field(default_factory=AtlasProviderBudget)
    department_allowlist: frozenset[str] = frozenset()
    role_allowlist: frozenset[str] = frozenset()
    data_classifications: frozenset[Literal["internal", "confidential", "restricted"]] = frozenset(
        {"internal"}
    )
    output_schema_version: str = "1.0"
    tags: frozenset[str] = frozenset()

    @field_validator("version")
    @classmethod
    def validate_semver(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("Provider version must use semantic versioning.")
        return value

    @field_validator("contract_version", "output_schema_version")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        if not CONTRACT_VERSION_PATTERN.fullmatch(value):
            raise ValueError("Contract versions must use major.minor semantic versioning.")
        return value

    @field_validator(
        "capabilities",
        "required_dependencies",
        "optional_dependencies",
        "department_allowlist",
        "role_allowlist",
        "tags",
    )
    @classmethod
    def validate_stable_identifiers(cls, values: frozenset[str]) -> frozenset[str]:
        if any(not STABLE_IDENTIFIER_PATTERN.fullmatch(value) for value in values):
            raise ValueError("Atlas definition identifiers must be stable machine identifiers.")
        return values

    @model_validator(mode="after")
    def validate_limits(self) -> AtlasProviderDefinition:
        if self.default_timeout_seconds > self.max_timeout_seconds:
            raise ValueError("Provider default timeout may not exceed its maximum timeout.")
        if self.default_budget.max_duration_seconds > self.max_timeout_seconds:
            raise ValueError("Provider default budget may not exceed its maximum timeout.")
        if self.required_dependencies.intersection(self.optional_dependencies):
            raise ValueError("Provider dependencies cannot be both required and optional.")
        return self


class AtlasProviderHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: AtlasHealthStatus = AtlasHealthStatus.HEALTHY
    checked_at: datetime = Field(default_factory=utc_now)
    duration_ms: float = Field(default=0.0, ge=0)
    safe_message: str = Field(default="Atlas provider health check completed.", max_length=240)
    dependency_states: dict[str, Literal["available", "unavailable", "unknown"]] = Field(
        default_factory=dict
    )
    consecutive_failures: int = Field(default=0, ge=0)
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None


class AtlasProviderReadiness(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ready: bool
    checked_at: datetime = Field(default_factory=utc_now)
    reason_category: str | None = Field(default=None, max_length=80)
    available_capabilities: frozenset[str] = frozenset()
    unavailable_capabilities: frozenset[str] = frozenset()

    @field_validator("available_capabilities", "unavailable_capabilities")
    @classmethod
    def validate_capabilities(cls, values: frozenset[str]) -> frozenset[str]:
        if any(not STABLE_IDENTIFIER_PATTERN.fullmatch(value) for value in values):
            raise ValueError("Capabilities must be stable machine identifiers.")
        return values


class AtlasRuntimeConfigurationSnapshot(BaseModel):
    """The small, non-secret configuration view available to a provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    health_timeout_seconds: float = Field(gt=0)
    initialize_timeout_seconds: float = Field(gt=0)
    shutdown_timeout_seconds: float = Field(gt=0)
    failure_threshold: int = Field(ge=1)
    recovery_threshold: int = Field(ge=1)


class AtlasProviderRuntimeRecord(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid")

    definition: AtlasProviderDefinition
    state: AtlasProviderLifecycleState = AtlasProviderLifecycleState.REGISTERED
    previous_state: AtlasProviderLifecycleState | None = None
    registered_at: datetime = Field(default_factory=utc_now)
    state_changed_at: datetime = Field(default_factory=utc_now)
    initialized_at: datetime | None = None
    stopped_at: datetime | None = None
    failure_reason_category: str | None = None
    consecutive_health_failures: int = Field(default=0, ge=0)
    consecutive_health_successes: int = Field(default=0, ge=0)
    last_health: AtlasProviderHealth | None = None
    last_readiness: AtlasProviderReadiness | None = None


class AtlasProviderRequest(BaseModel):
    """Future collection input placeholder; it intentionally carries no request content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class AtlasProviderCollectionContext(BaseModel):
    """Future collection context placeholder with no application-state access."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    budget: AtlasProviderBudget = Field(default_factory=AtlasProviderBudget)


class AtlasProviderResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    status: Literal["success", "partial", "unavailable"] = "success"
    output_schema_version: str = "1.0"
    data: dict[str, JsonValue] = Field(default_factory=dict, max_length=64)
    warnings: tuple[str, ...] = Field(default=(), max_length=16)
    safe_error_category: str | None = Field(default=None, max_length=80)

    @field_validator("output_schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if not CONTRACT_VERSION_PATTERN.fullmatch(value):
            raise ValueError("Output schema versions must use major.minor semantic versioning.")
        return value

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        validate_safe_json_keys(value)
        return value

    @model_validator(mode="after")
    def validate_bounded_serialization(self) -> AtlasProviderResult:
        from app.atlas.constants import ATLAS_MAX_PROVIDER_RESULT_BYTES

        serialized = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if len(serialized) > ATLAS_MAX_PROVIDER_RESULT_BYTES:
            raise ValueError("Atlas provider result exceeds its bounded size.")
        return self
