from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from time import perf_counter

from app.core.config import settings
from app.agents.context import BudgetExceeded
from app.agents.errors import AgentErrorCategory, AgentRuntimeError
from app.agents.metrics import agent_runtime_metrics
from app.agents.models import AgentLifecycleState, AgentResourceUsage
from app.supervisor.agent_registry import AgentRegistry
from app.supervisor.planner import validate_plan
from app.supervisor.schemas import AgentResult, AgentTask, ExecutionPlan
from app.services.service_errors import CompanyBrainServiceError


SupervisorEventCallback = Callable[[str, dict[str, object]], Awaitable[None]]
logger = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self, runtime_manager=None) -> None:
        self.runtime_manager = runtime_manager

    async def execute(
        self,
        plan: ExecutionPlan,
        registry: AgentRegistry,
        permissions: set[str],
        context,
        event_callback: SupervisorEventCallback | None = None,
    ) -> tuple[list[AgentResult], int, float]:
        validate_plan(plan, registry, permissions)
        results: dict[str, AgentResult] = {}
        tasks_by_id = {task.task_id: task for task in plan.tasks}
        running = 0
        peak = 0
        started = perf_counter()

        async def run_task(task: AgentTask) -> AgentResult:
            nonlocal running, peak
            required_failed = any(
                results[dependency].status != "success"
                and not tasks_by_id[dependency].optional
                for dependency in task.dependency_ids
            )
            if required_failed:
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=task.agent_id,
                    status="skipped",
                    error_category="required_dependency_failed",
                )
            selected_agent_id = task.agent_id
            resolution = None
            if self.runtime_manager and self.runtime_manager.initialized_at is not None:
                resolution = self.runtime_manager.resolve_capability(
                    task.capability,
                    permissions=permissions,
                    department=getattr(context, "department", None),
                    role=getattr(context, "role", None),
                    preferred_agent_id=task.agent_id,
                )
                if not resolution.selected_agent_id:
                    return AgentResult(
                        task_id=task.task_id,
                        agent_id=task.agent_id,
                        status="failed",
                        capability=task.capability,
                        agent_version=task.agent_version,
                        error_category=AgentErrorCategory.UNAVAILABLE.value,
                    )
                selected_agent_id = resolution.selected_agent_id
                definition = self.runtime_manager.registry.get(selected_agent_id).definition
                if event_callback:
                    await event_callback(
                        "agent_resolved",
                        {
                            "task_id": task.task_id,
                            "capability": task.capability,
                            "agent_id": selected_agent_id,
                            "agent_version": definition.version,
                        },
                    )
                    if self.runtime_manager.state_for(selected_agent_id) == AgentLifecycleState.DEGRADED:
                        await event_callback(
                            "agent_degraded",
                            {
                                "task_id": task.task_id,
                                "agent_id": selected_agent_id,
                                "safe_reason_category": "agent_degraded",
                            },
                        )
            dependencies = _validated_dependency_results(task, results)
            dependency_failures = [
                {
                    "agent_id": results[dependency].agent_id,
                    "error_category": (
                        results[dependency].error_category or "agent_dependency_failed"
                    ),
                }
                for dependency in task.dependency_ids
                if results[dependency].status != "success"
            ]
            runtime_task = task.model_copy(
                update={
                    "agent_id": selected_agent_id,
                    "inputs": {
                        **task.inputs,
                        "dependency_results": dependencies,
                        "dependency_failures": dependency_failures,
                    },
                }
            )
            budget = task.budget or getattr(context, "budget", None)
            timeout_seconds = (
                min(task.timeout_seconds, budget.timeout_seconds)
                if budget
                else task.timeout_seconds
            )
            task_context = (
                replace(
                    context,
                    task_id=task.task_id,
                    budget=budget,
                    deadline=datetime.now(timezone.utc)
                    + timedelta(seconds=timeout_seconds),
                )
                if budget
                else context
            )
            if event_callback:
                if task.agent_id == "response_composer_agent":
                    await event_callback("composition_started", {})
                await event_callback(
                    "agent_started",
                    {"task_id": task.task_id, "agent_id": task.agent_id},
                )
            running += 1
            peak = max(peak, running)
            task_started = perf_counter()
            if selected_agent_id == "response_composer_agent" and getattr(
                context, "instrumentation", None
            ):
                context.instrumentation.record_metric(
                    "agent_composer_task_start_ms",
                    round(
                        (task_started - context.instrumentation.request_started_at) * 1000,
                        3,
                    ),
                )
            execution_started = False
            try:
                if self.runtime_manager and self.runtime_manager.initialized_at is not None:
                    await self.runtime_manager.begin_execution(selected_agent_id)
                    execution_started = True
                async with asyncio.timeout(timeout_seconds):
                    result = await registry.get(selected_agent_id).execute(runtime_task, task_context)
                result = AgentResult.model_validate(result)
                if result.task_id != task.task_id or result.agent_id != selected_agent_id:
                    raise ValueError("Agent returned a mismatched result contract.")
                _validate_output_contract(task.output_contract, result.structured_output)
                result.evidence = _validated_evidence(
                    result.evidence,
                    max_items=budget.max_evidence_items if budget else 12,
                )
                usage = _resource_usage(runtime_task, result)
                if budget:
                    _enforce_budget(budget, usage)
                    result.structured_output = _bounded_output(
                        result.structured_output, budget.max_output_chars
                    )
                result.resource_usage = usage
                result.agent_version = registry.get(selected_agent_id).definition.version
                result.capability = task.capability
                agent_runtime_metrics.increment(
                    "agent_execution_success_count",
                    agent_id=selected_agent_id,
                    capability=task.capability,
                )
            except TimeoutError:
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=selected_agent_id,
                    status="timed_out",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    capability=task.capability,
                    agent_version=task.agent_version,
                    error_category=(
                        AgentErrorCategory.TASK_DEADLINE_EXCEEDED.value
                        if self.runtime_manager
                        else "supervisor_task_timeout"
                    ),
                )
                agent_runtime_metrics.increment("agent_execution_timeout_count", agent_id=selected_agent_id, capability=task.capability)
            except asyncio.CancelledError:
                agent_runtime_metrics.increment("agent_execution_cancelled_count", agent_id=selected_agent_id, capability=task.capability)
                raise
            except BudgetExceeded as exc:
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=selected_agent_id,
                    status="failed",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    capability=task.capability,
                    agent_version=task.agent_version,
                    error_category=AgentErrorCategory.BUDGET_EXCEEDED.value,
                )
                agent_runtime_metrics.increment("agent_budget_exceeded_count", agent_id=selected_agent_id, capability=task.capability)
                if event_callback:
                    await event_callback(
                        "budget_warning",
                        {
                            "task_id": task.task_id,
                            "agent_id": selected_agent_id,
                            "budget_category": exc.budget_category,
                        },
                    )
            except AgentRuntimeError as exc:
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=selected_agent_id,
                    status="failed",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    capability=task.capability,
                    agent_version=task.agent_version,
                    error_category=exc.category.value,
                )
            except CompanyBrainServiceError:
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=selected_agent_id,
                    status="failed",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    capability=task.capability,
                    agent_version=task.agent_version,
                    error_category=AgentErrorCategory.DEPENDENCY_FAILED.value,
                )
            except (ValueError, TypeError):
                logger.exception(
                    "agent.result_invalid agent_id=%s capability=%s",
                    selected_agent_id,
                    task.capability,
                )
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=selected_agent_id,
                    status="failed",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    capability=task.capability,
                    agent_version=task.agent_version,
                    error_category=(
                        AgentErrorCategory.RESULT_INVALID.value
                        if self.runtime_manager
                        else "supervisor_agent_failed"
                    ),
                )
            except Exception:
                logger.exception(
                    "agent.execution_failed agent_id=%s capability=%s",
                    selected_agent_id,
                    task.capability,
                )
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=selected_agent_id,
                    status="failed",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    capability=task.capability,
                    agent_version=task.agent_version,
                    error_category=(
                        AgentErrorCategory.INTERNAL_ERROR.value
                        if self.runtime_manager
                        else "supervisor_agent_failed"
                    ),
                )
            finally:
                if execution_started:
                    self.runtime_manager.end_execution(selected_agent_id)
                running -= 1
            agent_runtime_metrics.increment("agent_execution_count", agent_id=selected_agent_id, capability=task.capability)
            agent_runtime_metrics.duration(
                "agent_execution_duration_ms",
                round((perf_counter() - task_started) * 1000, 3),
                agent_id=selected_agent_id,
            )
            if event_callback:
                await event_callback(
                    "agent_completed",
                    {
                        "task_id": task.task_id,
                        "agent_id": task.agent_id,
                        "status": result.status,
                        "duration_ms": result.duration_ms,
                    },
                )
            return result

        try:
            async with asyncio.timeout(settings.ctv_one_supervisor_total_timeout_seconds):
                max_parallel = max(settings.ctv_one_supervisor_max_parallel_tasks, 1)
                while len(results) < len(plan.tasks):
                    ready = [
                        task
                        for task in plan.tasks
                        if task.task_id not in results
                        and all(dependency in results for dependency in task.dependency_ids)
                    ]
                    if not ready:
                        raise ValueError("Execution graph made no progress.")
                    parallel_ready = [
                        task
                        for task in ready
                        if registry.get(task.agent_id).definition.supports_parallel_execution
                    ]
                    serial_ready = [task for task in ready if task not in parallel_ready]
                    batches = [
                        parallel_ready[offset : offset + max_parallel]
                        for offset in range(0, len(parallel_ready), max_parallel)
                    ]
                    batches.extend([task] for task in serial_ready)
                    for batch in batches:
                        completed = await asyncio.gather(*(run_task(task) for task in batch))
                        results.update({result.task_id: result for result in completed})
        except TimeoutError:
            for task in plan.tasks:
                results.setdefault(
                    task.task_id,
                    AgentResult(
                        task_id=task.task_id,
                        agent_id=task.agent_id,
                        status="timed_out",
                        error_category="supervisor_total_timeout",
                    ),
                )
        return (
            [results[task.task_id] for task in plan.tasks],
            peak,
            round((perf_counter() - started) * 1000, 3),
        )


def _validated_evidence(items, *, max_items: int = 12):
    unique = []
    seen: set[str] = set()
    total_chars = 0
    for item in items:
        if item.evidence_id in seen or len(unique) >= max_items:
            continue
        remaining = 12000 - total_chars
        if remaining <= 0:
            break
        item.content = item.content[:remaining]
        total_chars += len(item.content)
        seen.add(item.evidence_id)
        unique.append(item)
    return unique


def _validated_dependency_results(
    task: AgentTask,
    results: dict[str, AgentResult],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    evidence_seen: set[str] = set()
    evidence_count = 0
    evidence_chars = 0
    for dependency in task.dependency_ids:
        result = results[dependency]
        if result.status != "success":
            continue
        dumped = result.model_dump(mode="json")
        bounded_evidence = []
        for item in dumped.get("evidence", []):
            evidence_id = str(item.get("evidence_id") or "")
            if evidence_id in evidence_seen or evidence_count >= 12:
                continue
            remaining = 12000 - evidence_chars
            if remaining <= 0:
                break
            item["content"] = str(item.get("content") or "")[:remaining]
            evidence_seen.add(evidence_id)
            evidence_count += 1
            evidence_chars += len(item["content"])
            bounded_evidence.append(item)
        dumped["evidence"] = bounded_evidence
        payload.append(dumped)
    return payload


def _validate_output_contract(contract: str, output: dict[str, object]) -> None:
    required: dict[str, dict[str, type]] = {
        "KnowledgeEvidenceV1": {"source_count": int, "facts": list},
        "OperationsSnapshotEvidenceV1": {
            "task_count": int,
            "board_count": int,
            "snapshot_context": str,
        },
        "EmployeeSelfContextV1": {"scope": str, "employee_context": str},
        "ReasoningSummaryV1": {"analysis": str},
        "CompanyBrainAnswerV1": {"answer": str},
    }
    for field, expected_type in required.get(contract, {}).items():
        if not isinstance(output.get(field), expected_type):
            raise ValueError("Agent returned a malformed output contract.")


def _resource_usage(task: AgentTask, result: AgentResult) -> AgentResourceUsage:
    inference_capabilities = {
        "compare", "synthesize", "recommend", "risk_analysis", "tradeoff_analysis",
        "executive_summary", "final_answer", "structured_brief",
    }
    retrieval_capabilities = {
        "knowledge_search", "policy_lookup", "document_summary", "evidence_retrieval",
        "operations_status", "overdue_tasks", "priorities", "workload_summary", "project_status",
        "employee_context", "responsibility_lookup", "role_context", "department_context",
    }
    return AgentResourceUsage(
        inference_calls=int(
            task.capability in inference_capabilities
            and result.composition_strategy != "deterministic"
        ),
        retrieval_calls=int(task.capability in retrieval_capabilities),
        evidence_items=len(result.evidence),
        input_chars=len(json.dumps(task.inputs, ensure_ascii=True)),
        output_chars=len(json.dumps(result.structured_output, ensure_ascii=True)),
    )


def _enforce_budget(budget, usage: AgentResourceUsage) -> None:
    checks = {
        "inference_calls": budget.max_inference_calls,
        "retrieval_calls": budget.max_retrieval_calls,
        "evidence_items": budget.max_evidence_items,
        "input_chars": budget.max_input_chars,
        "output_chars": budget.max_output_chars,
        "prompt_tokens_estimate": budget.max_prompt_tokens_estimate,
    }
    for field, maximum in checks.items():
        if getattr(usage, field) > maximum:
            raise BudgetExceeded(field)
    if usage.queue_wait_ms > budget.max_queue_wait_seconds * 1000:
        raise BudgetExceeded("queue_wait")


def _bounded_output(output: dict[str, object], maximum: int) -> dict[str, object]:
    if len(json.dumps(output, ensure_ascii=True)) <= maximum:
        return output
    raise BudgetExceeded("output_chars")
