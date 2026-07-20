from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter

from app.core.config import settings
from app.supervisor.agent_registry import AgentRegistry
from app.supervisor.planner import validate_plan
from app.supervisor.schemas import AgentResult, AgentTask, ExecutionPlan


SupervisorEventCallback = Callable[[str, dict[str, object]], Awaitable[None]]


class ExecutionEngine:
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
            dependencies = _validated_dependency_results(task, results)
            runtime_task = task.model_copy(
                update={"inputs": {**task.inputs, "dependency_results": dependencies}}
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
            try:
                async with asyncio.timeout(task.timeout_seconds):
                    result = await registry.get(task.agent_id).execute(runtime_task, context)
                result = AgentResult.model_validate(result)
                if result.task_id != task.task_id or result.agent_id != task.agent_id:
                    raise ValueError("Agent returned a mismatched result contract.")
                _validate_output_contract(task.output_contract, result.structured_output)
                result.evidence = _validated_evidence(result.evidence)
            except TimeoutError:
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=task.agent_id,
                    status="timed_out",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    error_category="supervisor_task_timeout",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=task.agent_id,
                    status="failed",
                    duration_ms=round((perf_counter() - task_started) * 1000, 3),
                    error_category="supervisor_agent_failed",
                )
            finally:
                running -= 1
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


def _validated_evidence(items):
    unique = []
    seen: set[str] = set()
    total_chars = 0
    for item in items:
        if item.evidence_id in seen or len(unique) >= 12:
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
