"""Provider-independent immutable runtime contracts; not wired to production routes."""
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Protocol


class RuntimeStatus(StrEnum):
    IDLE = "idle"; SUCCEEDED = "succeeded"; FAILED = "failed"; TIMED_OUT = "timed-out"; CANCELLED = "cancelled"; STALE = "stale"; REJECTED = "rejected"


class AttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"; FAILED = "failed"; TIMED_OUT = "timed-out"; CANCELLED = "cancelled"; INCOMPATIBLE = "incompatible-adapter"


class MessageRole(StrEnum):
    SYSTEM = "system"; USER = "user"; ASSISTANT = "assistant"


@dataclass(frozen=True)
class RuntimeMessage:
    """A serializable, provider-neutral conversation turn."""
    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", MessageRole(self.role))
        if not isinstance(self.content, str):
            raise TypeError("message content must be a string")

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass(frozen=True)
class RuntimeRequest:
    """Immutable runtime input. Message order is the tuple order and is never normalized."""
    execution_id: str
    plan: "ExecutionPlan"
    messages: tuple[RuntimeMessage, ...]
    cancelled: object | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.messages, tuple):
            raise TypeError("messages must be an immutable tuple")
        if not self.messages:
            raise ValueError("messages must not be empty")
        if not all(isinstance(message, RuntimeMessage) for message in self.messages):
            raise TypeError("messages must contain RuntimeMessage values")

    def to_dict(self) -> dict[str, object]:
        return {"execution_id": self.execution_id, "messages": [message.to_dict() for message in self.messages]}


@dataclass(frozen=True)
class AdapterDescriptor:
    adapter_id: str; provider_type: str; model_ids: tuple[str, ...]; locations: tuple[str, ...] = ("local",); modes: tuple[str, ...] = ("synchronous",); enabled: bool = True; priority: int = 0


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str; fingerprint: str; context_id: str; registry_version: str; model_id: str; provider_type: str; location: str = "local"; mode: str = "synchronous"; fallback_model_ids: tuple[str, ...] = (); timeout_ms: int = 120000; max_retries: int = 0


@dataclass(frozen=True)
class AdapterResult:
    status: RuntimeStatus; adapter_id: str; model_id: str; output: str | None = None; error_code: str | None = None; error_category: str | None = None; retryable: bool = False; fallback_eligible: bool = False; usage: tuple[tuple[str, int], ...] = (); metadata: tuple[tuple[str, str], ...] = ()


class ModelAdapter(Protocol):
    descriptor: AdapterDescriptor
    def supports(self, *, model_id: str, provider_type: str, location: str, mode: str) -> bool: ...
    async def execute(self, *, execution_id: str, model_id: str, messages: tuple[RuntimeMessage, ...], cancelled: object | None = None) -> AdapterResult: ...


@dataclass(frozen=True)
class ExecutionAttempt:
    attempt_id: str; sequence: int; model_id: str; adapter_id: str | None; status: AttemptStatus; retry_index: int; fallback_index: int; error_code: str | None = None


@dataclass(frozen=True)
class RuntimeResult:
    execution_id: str; status: RuntimeStatus; plan_id: str; fingerprint: str; output: str | None; completed_model_id: str | None; completed_adapter_id: str | None; attempts: tuple[ExecutionAttempt, ...]; diagnostics: tuple[str, ...]; statistics: tuple[tuple[str, int], ...]; metadata: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe copy without retaining request messages."""
        return asdict(self)
