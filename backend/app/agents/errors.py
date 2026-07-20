from __future__ import annotations

from enum import StrEnum


class AgentErrorCategory(StrEnum):
    DISABLED = "agent_disabled"
    UNAVAILABLE = "agent_unavailable"
    NOT_READY = "agent_not_ready"
    INITIALIZATION_FAILED = "agent_initialization_failed"
    HEALTH_FAILED = "agent_health_failed"
    DEPENDENCY_UNAVAILABLE = "agent_dependency_unavailable"
    PERMISSION_DENIED = "agent_permission_denied"
    CAPABILITY_UNSUPPORTED = "agent_capability_unsupported"
    CONTRACT_MISMATCH = "agent_contract_mismatch"
    BUDGET_EXCEEDED = "agent_budget_exceeded"
    QUEUE_TIMEOUT = "agent_queue_timeout"
    EXECUTION_TIMEOUT = "agent_execution_timeout"
    TASK_DEADLINE_EXCEEDED = "agent_task_deadline_exceeded"
    CANCELLED = "agent_cancelled"
    RESULT_INVALID = "agent_result_invalid"
    DEPENDENCY_FAILED = "agent_dependency_failed"
    INTERNAL_ERROR = "agent_internal_error"


SAFE_AGENT_MESSAGES: dict[AgentErrorCategory, str] = {
    AgentErrorCategory.DISABLED: "The selected agent is disabled.",
    AgentErrorCategory.UNAVAILABLE: "The selected agent is unavailable.",
    AgentErrorCategory.NOT_READY: "The selected agent is not ready.",
    AgentErrorCategory.INITIALIZATION_FAILED: "The agent could not be initialized.",
    AgentErrorCategory.HEALTH_FAILED: "The agent health check failed.",
    AgentErrorCategory.DEPENDENCY_UNAVAILABLE: "A required agent dependency is unavailable.",
    AgentErrorCategory.PERMISSION_DENIED: "The requested agent capability is not permitted.",
    AgentErrorCategory.CAPABILITY_UNSUPPORTED: "The requested capability is unsupported.",
    AgentErrorCategory.CONTRACT_MISMATCH: "The agent contract is incompatible.",
    AgentErrorCategory.BUDGET_EXCEEDED: "The agent execution budget was exceeded.",
    AgentErrorCategory.QUEUE_TIMEOUT: "The agent could not enter the inference queue in time.",
    AgentErrorCategory.EXECUTION_TIMEOUT: "The agent execution timed out.",
    AgentErrorCategory.TASK_DEADLINE_EXCEEDED: "The agent task deadline was exceeded.",
    AgentErrorCategory.CANCELLED: "The agent execution was cancelled.",
    AgentErrorCategory.RESULT_INVALID: "The agent returned an invalid result.",
    AgentErrorCategory.DEPENDENCY_FAILED: "An agent dependency failed.",
    AgentErrorCategory.INTERNAL_ERROR: "The agent failed safely.",
}


class AgentRuntimeError(RuntimeError):
    def __init__(self, category: AgentErrorCategory, safe_message: str | None = None) -> None:
        self.category = category
        self.safe_message = safe_message or SAFE_AGENT_MESSAGES[category]
        super().__init__(self.safe_message)


class AgentRegistrationError(ValueError):
    pass
