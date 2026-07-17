from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.context_requirements import ContextRequirements
from app.db.models.user import User
from app.schemas.context import ContextBundle
from app.schemas.knowledge import KnowledgeSource
from app.services import conversation_service
from app.services.context_engine import context_engine
from app.services.intelligence_router import RouteDecision
from app.services.operations_context_service import (
    OperationsContext,
    operations_context_service,
)
from app.services.performance_instrumentation import AskPerformanceInstrumentation
from app.services.service_errors import CompanyBrainServiceError

KnowledgeFetcher = Callable[
    [str, int, list[str], AskPerformanceInstrumentation | None],
    Awaitable[list[KnowledgeSource]],
]


@dataclass(frozen=True)
class ComponentOutcome:
    component: str
    required: bool
    status: str
    duration_ms: float
    value: object | None = None
    error_category: str | None = None
    status_code: int = 503
    safe_detail: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == "success"

    @property
    def unavailable(self) -> bool:
        return self.status in {"failed", "timed_out"}


@dataclass(frozen=True)
class ContextRetrievalResult:
    knowledge: list[KnowledgeSource] = field(default_factory=list)
    operations: OperationsContext | None = None
    employee: ContextBundle | None = None
    history: str = ""
    component_statuses: dict[str, str] = field(default_factory=dict)
    component_durations_ms: dict[str, float] = field(default_factory=dict)
    total_retrieval_duration_ms: float = 0.0
    parallel_execution_used: bool = False
    required_context_components: list[str] = field(default_factory=list)
    successful_context_components: list[str] = field(default_factory=list)
    failed_context_components: list[str] = field(default_factory=list)
    timed_out_context_components: list[str] = field(default_factory=list)
    unavailable_context_components: list[str] = field(default_factory=list)
    required_context_failure: str | None = None

    @property
    def context_degraded(self) -> bool:
        return bool(self.unavailable_context_components)


class ContextRetrievalCoordinator:
    async def retrieve(
        self,
        *,
        question: str,
        top_k: int,
        routed_collections: list[str],
        requirements: ContextRequirements,
        route: RouteDecision,
        current_user: User,
        db: AsyncSession,
        conversation_id: UUID | None,
        knowledge_fetcher: KnowledgeFetcher,
        instrumentation: AskPerformanceInstrumentation | None = None,
    ) -> ContextRetrievalResult:
        started_at = perf_counter()
        required = self.required_components(requirements, route)
        outcomes: dict[str, ComponentOutcome] = {}
        top_level_task_count = 0

        async def fetch_knowledge() -> ComponentOutcome:
            return await self._run_component(
                "knowledge",
                required="knowledge" in required,
                timeout_seconds=settings.company_brain_knowledge_timeout_seconds,
                instrumentation=instrumentation,
                stage_name="knowledge_retrieval",
                fetch=lambda: knowledge_fetcher(
                    question,
                    min(top_k, requirements.max_knowledge_chunks),
                    routed_collections,
                    instrumentation,
                ),
            )

        async def fetch_operations() -> ComponentOutcome:
            return await self._run_component(
                "operations",
                required="operations" in required,
                timeout_seconds=settings.company_brain_operations_timeout_seconds,
                instrumentation=instrumentation,
                stage_name="operational_context",
                fetch=lambda: operations_context_service.build(
                    question,
                    force=True,
                    max_tasks=requirements.max_operational_tasks,
                    max_chars=requirements.max_operational_chars,
                ),
            )

        async def fetch_database_contexts() -> list[ComponentOutcome]:
            db_outcomes: list[ComponentOutcome] = []
            if requirements.include_employee:
                db_outcomes.append(
                    await self._run_component(
                        "employee",
                        required="employee" in required,
                        timeout_seconds=settings.company_brain_employee_timeout_seconds,
                        instrumentation=instrumentation,
                        stage_name="employee_context",
                        fetch=lambda: context_engine.build_employee_context(
                            db,
                            current_user,
                            question=question,
                            route=route,
                            instrumentation=instrumentation,
                            include_operations=False,
                            max_employee_context_chars=(
                                requirements.max_employee_context_chars
                            ),
                        ),
                    )
                )
            if requirements.include_history and conversation_id is not None:
                db_outcomes.append(
                    await self._run_component(
                        "history",
                        required="history" in required,
                        timeout_seconds=settings.company_brain_history_timeout_seconds,
                        instrumentation=instrumentation,
                        stage_name="history_loading",
                        fetch=lambda: self._load_history(
                            db,
                            current_user,
                            conversation_id,
                            max_messages=requirements.max_history_messages,
                            max_chars=requirements.max_history_chars,
                            current_question=question,
                        ),
                    )
                )
            return db_outcomes

        tasks: dict[str, asyncio.Task[ComponentOutcome | list[ComponentOutcome]]] = {}
        try:
            async with asyncio.TaskGroup() as task_group:
                if requirements.include_knowledge:
                    top_level_task_count += 1
                    tasks["knowledge"] = task_group.create_task(fetch_knowledge())
                if requirements.include_operations:
                    top_level_task_count += 1
                    tasks["operations"] = task_group.create_task(fetch_operations())
                if requirements.include_employee or (
                    requirements.include_history and conversation_id is not None
                ):
                    top_level_task_count += 1
                    tasks["database_contexts"] = task_group.create_task(
                        fetch_database_contexts()
                    )
        except asyncio.CancelledError:
            raise

        for task in tasks.values():
            result = task.result()
            if isinstance(result, list):
                for item in result:
                    outcomes[item.component] = item
            else:
                outcomes[result.component] = result

        total_ms = round((perf_counter() - started_at) * 1000, 3)
        result = self._result_from_outcomes(
            outcomes=outcomes,
            required=required,
            total_ms=total_ms,
            parallel_execution_used=top_level_task_count > 1,
        )
        if instrumentation:
            instrumentation.record_context_retrieval(
                parallel_execution_used=result.parallel_execution_used,
                component_durations_ms=result.component_durations_ms,
                total_retrieval_duration_ms=result.total_retrieval_duration_ms,
                required_components=result.required_context_components,
                successful_components=result.successful_context_components,
                failed_components=result.failed_context_components,
                timed_out_components=result.timed_out_context_components,
                context_degraded=result.context_degraded,
                unavailable_components=result.unavailable_context_components,
                required_context_failure=result.required_context_failure,
            )
        result_failure = self._required_failure(outcomes)
        if result_failure is not None:
            raise result_failure
        return result

    def required_components(
        self,
        requirements: ContextRequirements,
        route: RouteDecision,
    ) -> list[str]:
        required: list[str] = []
        if requirements.include_knowledge:
            required.append("knowledge")
        if requirements.include_operations:
            required.append("operations")
        if requirements.include_employee and route.intent == "employee":
            required.append("employee")
        return required

    async def _run_component(
        self,
        component: str,
        *,
        required: bool,
        timeout_seconds: float,
        instrumentation: AskPerformanceInstrumentation | None,
        stage_name: str,
        fetch: Callable[[], Awaitable[object]],
    ) -> ComponentOutcome:
        started_at = perf_counter()
        try:
            value = await asyncio.wait_for(fetch(), timeout=timeout_seconds)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            if instrumentation:
                instrumentation.add_duration(stage_name, duration_ms / 1000)
            return ComponentOutcome(
                component=component,
                required=required,
                status="timed_out",
                duration_ms=duration_ms,
                error_category=f"context_{component}_timeout",
                status_code=504,
                safe_detail=f"Required {component} context timed out.",
            )
        except CompanyBrainServiceError as exc:
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            if instrumentation:
                instrumentation.add_duration(stage_name, duration_ms / 1000)
            return ComponentOutcome(
                component=component,
                required=required,
                status="failed",
                duration_ms=duration_ms,
                error_category=exc.category,
                status_code=exc.status_code,
                safe_detail=exc.safe_detail,
            )
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            if instrumentation:
                instrumentation.add_duration(stage_name, duration_ms / 1000)
            return ComponentOutcome(
                component=component,
                required=required,
                status="failed",
                duration_ms=duration_ms,
                error_category=f"context_{component}_unavailable",
                safe_detail=f"Required {component} context is temporarily unavailable.",
            )

        duration_ms = round((perf_counter() - started_at) * 1000, 3)
        if instrumentation:
            instrumentation.add_duration(stage_name, duration_ms / 1000)
        return ComponentOutcome(
            component=component,
            required=required,
            status="success",
            duration_ms=duration_ms,
            value=value,
        )

    async def _load_history(
        self,
        db: AsyncSession,
        user: User,
        conversation_id: UUID,
        *,
        max_messages: int,
        max_chars: int,
        current_question: str,
    ) -> str:
        if max_messages <= 0:
            return ""
        messages = await conversation_service.recent_messages(
            db,
            user,
            conversation_id,
            limit=max_messages + 1,
        )
        lines: list[str] = []
        for message in messages:
            content = message.content.strip()
            if not content:
                continue
            if message.role.value == "user" and content == current_question.strip():
                continue
            role = "User" if message.role.value == "user" else "Assistant"
            lines.append(f"{role}: {content}")
        text = "\n".join(lines[-max_messages:])
        return _cap_text(text, max_chars)[0]

    def _result_from_outcomes(
        self,
        *,
        outcomes: dict[str, ComponentOutcome],
        required: list[str],
        total_ms: float,
        parallel_execution_used: bool,
    ) -> ContextRetrievalResult:
        successful = [
            component
            for component, outcome in outcomes.items()
            if outcome.status == "success"
        ]
        failed = [
            component
            for component, outcome in outcomes.items()
            if outcome.status == "failed"
        ]
        timed_out = [
            component
            for component, outcome in outcomes.items()
            if outcome.status == "timed_out"
        ]
        unavailable = [
            component
            for component, outcome in outcomes.items()
            if outcome.unavailable and not outcome.required
        ]
        required_failure = next(
            (
                outcome.error_category
                for outcome in outcomes.values()
                if outcome.required and outcome.unavailable
            ),
            None,
        )

        knowledge_value = outcomes.get("knowledge")
        operations_value = outcomes.get("operations")
        employee_value = outcomes.get("employee")
        history_value = outcomes.get("history")

        return ContextRetrievalResult(
            knowledge=(
                knowledge_value.value
                if knowledge_value and isinstance(knowledge_value.value, list)
                else []
            ),
            operations=(
                operations_value.value
                if operations_value and isinstance(operations_value.value, OperationsContext)
                else None
            ),
            employee=(
                employee_value.value
                if employee_value and isinstance(employee_value.value, ContextBundle)
                else None
            ),
            history=history_value.value if history_value and isinstance(history_value.value, str) else "",
            component_statuses={
                component: outcome.status
                for component, outcome in sorted(outcomes.items())
            },
            component_durations_ms={
                component: outcome.duration_ms
                for component, outcome in sorted(outcomes.items())
            },
            total_retrieval_duration_ms=total_ms,
            parallel_execution_used=parallel_execution_used,
            required_context_components=list(required),
            successful_context_components=successful,
            failed_context_components=failed,
            timed_out_context_components=timed_out,
            unavailable_context_components=unavailable,
            required_context_failure=required_failure,
        )

    def _required_failure(
        self,
        outcomes: dict[str, ComponentOutcome],
    ) -> CompanyBrainServiceError | None:
        failed_required = next(
            (
                outcome
                for outcome in outcomes.values()
                if outcome.required and outcome.unavailable
            ),
            None,
        )
        if failed_required is None:
            return None
        return CompanyBrainServiceError(
            category=failed_required.error_category,
            status_code=failed_required.status_code,
            safe_detail=failed_required.safe_detail,
            diagnostics={"has_error": True},
        )


def _cap_text(value: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(value) <= max_chars:
        return value, False
    if max_chars <= 20:
        return value[:max_chars], True
    return value[: max_chars - 15].rstrip() + "\n[Truncated]", True


context_retrieval_coordinator = ContextRetrievalCoordinator()
