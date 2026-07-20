from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


SupervisorMode = Literal["direct", "supervised", "fallback_direct"]
RequestedSupervisorMode = Literal["auto", "direct", "supervised"]
AgentStatus = Literal["success", "failed", "timed_out", "skipped"]


class SupervisorRequest(BaseModel):
    request_id: str
    user_id: str
    conversation_id: str | None = None
    question: str
    permissions: set[str] = Field(default_factory=set)
    streaming: bool = False
    requested_output_format: str = "answer"


class EvidenceItem(BaseModel):
    evidence_id: str
    citation: str
    source_type: Literal["knowledge", "operations", "employee"]
    content: str = Field(max_length=2000)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AgentTask(BaseModel):
    task_id: str
    agent_id: str
    capability: str
    objective: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    dependency_ids: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=60.0, gt=0)
    optional: bool = False
    output_contract: str


class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    mode: Literal["supervised"] = "supervised"
    objective: str
    tasks: list[AgentTask]
    estimated_complexity: Literal["moderate", "complex"] = "moderate"
    required_agents: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    planner_version: str = "v2-c1-deterministic"
    planner_type: Literal["deterministic", "llm"] = "deterministic"


class AgentResult(BaseModel):
    task_id: str
    agent_id: str
    status: AgentStatus
    structured_output: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    cache_metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )
    error_category: str | None = None


class SupervisorResult(BaseModel):
    plan_id: str
    mode: SupervisorMode
    task_results: list[AgentResult]
    final_answer: str
    citations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    partial: bool = False
    metrics: dict[str, str | int | float | bool | list[str] | None] = Field(
        default_factory=dict
    )


class AgentDefinition(BaseModel):
    agent_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    description: str
    capabilities: frozenset[str]
    supported_intents: frozenset[str]
    required_permissions: frozenset[str]
    input_schema: str
    output_schema: str
    estimated_cost_class: Literal["light", "standard", "reasoning"]
    supports_parallel_execution: bool = True
    enabled: bool = True
    version: str = "1.0"
