from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.agents.models import AgentExecutionBudget, AgentResourceUsage


class KnowledgeFetcher(Protocol):
    async def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class AgentRuntimeServices:
    """Explicit, narrow service handles available to the built-in plugin only."""

    database_adapter: Any
    knowledge_fetcher: KnowledgeFetcher
    instrumentation: Any = None


@dataclass(frozen=True)
class AgentExecutionContext:
    request_id: str
    plan_id: str
    task_id: str
    authenticated_user_snapshot: Any
    permissions: frozenset[str]
    department: str | None
    role: str | None
    conversation_id: str | None
    streaming: bool
    deadline: datetime | None
    budget: AgentExecutionBudget
    runtime_services: AgentRuntimeServices
    trace_context: dict[str, str] = field(default_factory=dict)
    cancellation_event: asyncio.Event = field(default_factory=asyncio.Event)
    question: str = ""
    top_k: int = 5
    route: Any = None
    requirements: Any = None

    @property
    def user(self) -> Any:
        return self.authenticated_user_snapshot

    @property
    def db(self) -> Any:
        return self.runtime_services.database_adapter

    @property
    def knowledge_fetcher(self) -> KnowledgeFetcher:
        return self.runtime_services.knowledge_fetcher

    @property
    def instrumentation(self) -> Any:
        return self.runtime_services.instrumentation


class AgentBudgetTracker:
    def __init__(self, budget: AgentExecutionBudget) -> None:
        self.budget = budget
        self.usage = AgentResourceUsage()

    def inference_call(self) -> None:
        self.usage.inference_calls += 1
        self._check("inference_calls", self.budget.max_inference_calls)

    def retrieval_call(self) -> None:
        self.usage.retrieval_calls += 1
        self._check("retrieval_calls", self.budget.max_retrieval_calls)

    def evidence(self, count: int) -> None:
        self.usage.evidence_items += max(count, 0)
        self._check("evidence_items", self.budget.max_evidence_items)

    def output(self, characters: int) -> None:
        self.usage.output_chars += max(characters, 0)
        self._check("output_chars", self.budget.max_output_chars)

    def input(self, characters: int) -> None:
        self.usage.input_chars += max(characters, 0)
        self._check("input_chars", self.budget.max_input_chars)

    def queue_wait(self, milliseconds: float) -> None:
        self.usage.queue_wait_ms += max(milliseconds, 0.0)
        if self.usage.queue_wait_ms > self.budget.max_queue_wait_seconds * 1000:
            raise BudgetExceeded("queue_wait")

    def _check(self, field_name: str, maximum: int) -> None:
        if getattr(self.usage, field_name) > maximum:
            raise BudgetExceeded(field_name)


class BudgetExceeded(RuntimeError):
    def __init__(self, category: str) -> None:
        self.budget_category = category
        super().__init__("Agent execution budget exceeded.")

