from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


AGENT_RUNTIME_CONTRACT_VERSION = "1.0"
SUPERVISOR_PLAN_CONTRACT_VERSION = "1.0"
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentLifecycleState(StrEnum):
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    DRAINING = "draining"
    STOPPED = "stopped"
    FAILED = "failed"


class DependencyIdentifier(StrEnum):
    KNOWLEDGE_SERVICE = "knowledge_service"
    OPERATIONS_SNAPSHOT_SERVICE = "operations_snapshot_service"
    EMPLOYEE_INTELLIGENCE_SERVICE = "employee_intelligence_service"
    INFERENCE_QUEUE = "inference_queue"
    OLLAMA_CLIENT = "ollama_client"
    SEMANTIC_CACHE = "semantic_cache"
    DATABASE_ADAPTER = "database_adapter"


class AgentExecutionBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    timeout_seconds: float = Field(default=60.0, gt=0)
    max_inference_calls: int = Field(default=1, ge=0)
    max_retrieval_calls: int = Field(default=3, ge=0)
    max_evidence_items: int = Field(default=12, ge=0)
    max_input_chars: int = Field(default=16000, ge=1)
    max_output_chars: int = Field(default=16000, ge=1)
    max_prompt_tokens_estimate: int = Field(default=8000, ge=1)
    max_queue_wait_seconds: float = Field(default=120.0, gt=0)
    cost_class: Literal["light", "standard", "reasoning"] = "standard"
    allow_partial: bool = True

    def bounded_by(self, maximum: AgentExecutionBudget) -> AgentExecutionBudget:
        """Return a budget that cannot exceed server-owned maxima."""
        return AgentExecutionBudget(
            timeout_seconds=min(self.timeout_seconds, maximum.timeout_seconds),
            max_inference_calls=min(self.max_inference_calls, maximum.max_inference_calls),
            max_retrieval_calls=min(self.max_retrieval_calls, maximum.max_retrieval_calls),
            max_evidence_items=min(self.max_evidence_items, maximum.max_evidence_items),
            max_input_chars=min(self.max_input_chars, maximum.max_input_chars),
            max_output_chars=min(self.max_output_chars, maximum.max_output_chars),
            max_prompt_tokens_estimate=min(
                self.max_prompt_tokens_estimate, maximum.max_prompt_tokens_estimate
            ),
            max_queue_wait_seconds=min(
                self.max_queue_wait_seconds, maximum.max_queue_wait_seconds
            ),
            cost_class=self.cost_class,
            allow_partial=self.allow_partial and maximum.allow_partial,
        )


class AgentResourceUsage(BaseModel):
    inference_calls: int = Field(default=0, ge=0)
    retrieval_calls: int = Field(default=0, ge=0)
    evidence_items: int = Field(default=0, ge=0)
    input_chars: int = Field(default=0, ge=0)
    output_chars: int = Field(default=0, ge=0)
    prompt_tokens_estimate: int = Field(default=0, ge=0)
    queue_wait_ms: float = Field(default=0.0, ge=0)


class AgentDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    agent_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(validation_alias=AliasChoices("display_name", "name"))
    description: str
    version: str = "1.0.0"
    contract_version: str = AGENT_RUNTIME_CONTRACT_VERSION
    capabilities: frozenset[str]
    supported_intents: frozenset[str]
    required_permissions: frozenset[str]
    required_dependencies: frozenset[DependencyIdentifier] = frozenset()
    optional_dependencies: frozenset[DependencyIdentifier] = frozenset()
    required: bool = False
    enabled_by_default: bool = Field(
        default=True,
        validation_alias=AliasChoices("enabled_by_default", "enabled"),
    )
    supports_parallel_execution: bool = True
    supports_streaming: bool = False
    estimated_cost_class: Literal["light", "standard", "reasoning"]
    default_timeout_seconds: float = Field(default=60.0, gt=0)
    max_timeout_seconds: float = Field(default=180.0, gt=0)
    default_budget: AgentExecutionBudget = Field(default_factory=AgentExecutionBudget)
    department_allowlist: frozenset[str] = frozenset()
    role_allowlist: frozenset[str] = frozenset()
    input_schema_version: str = Field(
        validation_alias=AliasChoices("input_schema_version", "input_schema")
    )
    output_schema_version: str = Field(
        validation_alias=AliasChoices("output_schema_version", "output_schema")
    )
    tags: frozenset[str] = frozenset()
    priority: int = Field(default=100, ge=0)

    @field_validator("version")
    @classmethod
    def validate_semver(cls, value: str) -> str:
        normalized = value if value.count(".") >= 2 else f"{value}.0"
        if not SEMVER_PATTERN.fullmatch(normalized):
            raise ValueError("Agent version must use semantic versioning.")
        return normalized

    @property
    def name(self) -> str:
        return self.display_name

    @property
    def input_schema(self) -> str:
        return self.input_schema_version

    @property
    def output_schema(self) -> str:
        return self.output_schema_version

    @property
    def enabled(self) -> bool:
        return self.enabled_by_default


class CapabilityDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str
    input_schema: str
    output_schema: str
    required_permissions: frozenset[str]
    data_classification: Literal["internal", "confidential", "restricted"] = "internal"
    read_only: bool = True
    external_side_effects: bool = False
    supports_streaming: bool = False
    default_timeout_seconds: float = Field(default=60.0, gt=0)
    max_result_size: int = Field(default=16000, ge=1)
    evidence_required: bool = False
    compatible_agent_contract_versions: frozenset[str] = frozenset({"1.0"})
    deprecated: bool = False
    replacement_capability: str | None = None
    allow_partial: bool = True


class CapabilityResolution(BaseModel):
    capability_id: str
    selected_agent_id: str | None = None
    candidate_agent_ids: list[str] = Field(default_factory=list)
    excluded_candidates: dict[str, str] = Field(default_factory=dict)
    resolution_reason: str
    fallback_available: bool = False
    contract_version: str = AGENT_RUNTIME_CONTRACT_VERSION
    resolution_duration_ms: float = 0.0


class AgentHealth(BaseModel):
    status: Literal["healthy", "degraded", "unavailable"]
    checked_at: datetime = Field(default_factory=utc_now)
    duration_ms: float = 0.0
    safe_message: str = "Agent health check completed."
    dependency_statuses: dict[str, str] = Field(default_factory=dict)
    consecutive_failures: int = 0
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None


class AgentReadiness(BaseModel):
    ready: bool
    reason_category: str | None = None
    checked_at: datetime = Field(default_factory=utc_now)
    capability_availability: dict[str, bool] = Field(default_factory=dict)


class AgentRuntimeContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    dependencies: dict[DependencyIdentifier, Any] = Field(default_factory=dict)


class RuntimeAgentRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    definition: AgentDefinition
    state: AgentLifecycleState = AgentLifecycleState.REGISTERED
    registered_at: datetime = Field(default_factory=utc_now)
    initialized_at: datetime | None = None
    state_changed_at: datetime = Field(default_factory=utc_now)
    draining_at: datetime | None = None
    stopped_at: datetime | None = None
    last_health: AgentHealth | None = None
    consecutive_health_failures: int = 0
    consecutive_health_successes: int = 0
    active_executions: int = 0
    safe_error_category: str | None = None
