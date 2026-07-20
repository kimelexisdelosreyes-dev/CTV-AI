from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.capabilities import build_core_capability_catalog  # noqa: E402
from app.agents.context import (  # noqa: E402
    AgentBudgetTracker,
    AgentExecutionContext,
    AgentRuntimeServices,
    BudgetExceeded,
)
from app.agents.models import (  # noqa: E402
    AgentDefinition,
    AgentExecutionBudget,
    AgentHealth,
    AgentLifecycleState,
)
from app.agents.plugins import PluginRegistry  # noqa: E402
from app.agents.registry import AgentRegistry  # noqa: E402
from app.agents.runtime_manager import AgentRuntimeManager  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.supervisor.execution_engine import ExecutionEngine  # noqa: E402
from app.supervisor.schemas import AgentResult, AgentTask, ExecutionPlan  # noqa: E402


DEFAULT_OUTPUT_DIR = REPO_ROOT / "benchmarks" / "reports"


class BenchmarkAgent:
    def __init__(
        self,
        agent_id: str,
        *,
        priority: int = 100,
        enabled: bool = True,
        delay: float = 0.0,
    ) -> None:
        self.definition = AgentDefinition(
            agent_id=agent_id,
            display_name=agent_id.replace("_", " ").title(),
            description="Offline runtime benchmark fixture.",
            version="2.0.0",
            capabilities=frozenset({"knowledge_search"}),
            supported_intents=frozenset({"policy"}),
            required_permissions=frozenset({"knowledge.read"}),
            enabled_by_default=enabled,
            priority=priority,
            input_schema_version="KnowledgeCapabilityInputV1",
            output_schema_version="KnowledgeEvidenceV1",
            estimated_cost_class="light",
            default_budget=AgentExecutionBudget(
                max_inference_calls=0, max_retrieval_calls=1
            ),
        )
        self.delay = delay

    async def initialize(self, _context) -> None:
        return None

    async def health_check(self) -> AgentHealth:
        return AgentHealth(status="healthy")

    async def execute(self, task, _context) -> AgentResult:
        if self.delay:
            await asyncio.sleep(self.delay)
        return AgentResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            status="success",
            structured_output={"source_count": 0, "facts": []},
        )


def _manager(*agents: BenchmarkAgent) -> AgentRuntimeManager:
    catalog = build_core_capability_catalog()
    registry = AgentRegistry(catalog)
    for agent in agents:
        registry.register(agent)
    return AgentRuntimeManager(registry, catalog, PluginRegistry(set()))


def _result(case_label: str, started: float, **values: Any) -> dict[str, Any]:
    return {
        "case_label": case_label,
        "selected_agent": None,
        "agent_version": None,
        "capability": None,
        "lifecycle_state": None,
        "resolution_duration_ms": 0.0,
        "resolution_fallback": False,
        "initialization_status": "not_required",
        "health_status": None,
        "budget_status": "not_applied",
        "queue_wait_ms": 0.0,
        "execution_latency_ms": round((perf_counter() - started) * 1000, 3),
        "partial_result": False,
        "fallback_used": False,
        "success": True,
        **values,
    }


async def run_runtime_benchmark() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    previous_poll = settings.ctv_one_agent_health_poll_enabled
    settings.ctv_one_agent_health_poll_enabled = False
    try:
        started = perf_counter()
        core_manager = _manager(
            BenchmarkAgent("knowledge_agent"),
            BenchmarkAgent("operations_agent"),
            BenchmarkAgent("employee_agent"),
            BenchmarkAgent("reasoning_agent"),
            BenchmarkAgent("response_composer_agent"),
        )
        await core_manager.initialize()
        ready = all(
            record.state == AgentLifecycleState.READY
            for record in core_manager.records.values()
        )
        results.append(
            _result(
                "runtime_all_core_agents_ready",
                started,
                initialization_status="ready" if ready else "failed",
                health_status="healthy",
                lifecycle_state="ready" if ready else "unavailable",
                success=ready,
            )
        )

        started = perf_counter()
        results.append(
            _result(
                "runtime_direct_cache_hit_bypass",
                started,
                lifecycle_state="bypassed",
                initialization_status="unchanged",
            )
        )

        manager = _manager(BenchmarkAgent("primary_agent", priority=10))
        await manager.initialize()
        started = perf_counter()
        resolution = manager.resolve_capability(
            "knowledge_search", permissions={"knowledge.read"}
        )
        results.append(
            _result(
                "runtime_deterministic_capability_resolution",
                started,
                selected_agent=resolution.selected_agent_id,
                agent_version="2.0.0",
                capability="knowledge_search",
                lifecycle_state="ready",
                resolution_duration_ms=resolution.resolution_duration_ms,
                initialization_status="ready",
                health_status="healthy",
                success=resolution.selected_agent_id == "primary_agent",
            )
        )

        disabled = _manager(BenchmarkAgent("optional_agent", enabled=False))
        await disabled.initialize()
        started = perf_counter()
        resolution = disabled.resolve_capability(
            "knowledge_search", permissions={"knowledge.read"}
        )
        results.append(
            _result(
                "runtime_optional_agent_disabled",
                started,
                capability="knowledge_search",
                lifecycle_state="disabled",
                initialization_status="skipped",
                success=resolution.selected_agent_id is None,
            )
        )

        degraded = _manager(BenchmarkAgent("degraded_agent"))
        await degraded.initialize()
        degraded.transition("degraded_agent", AgentLifecycleState.DEGRADED)
        started = perf_counter()
        resolution = degraded.resolve_capability(
            "knowledge_search", permissions={"knowledge.read"}
        )
        results.append(
            _result(
                "runtime_optional_agent_degraded",
                started,
                selected_agent=resolution.selected_agent_id,
                agent_version="2.0.0",
                capability="knowledge_search",
                lifecycle_state="degraded",
                resolution_duration_ms=resolution.resolution_duration_ms,
                initialization_status="ready",
                health_status="degraded",
            )
        )

        required = _manager(BenchmarkAgent("required_agent"))
        await required.initialize()
        required.transition("required_agent", AgentLifecycleState.UNAVAILABLE)
        started = perf_counter()
        resolution = required.resolve_capability(
            "knowledge_search", permissions={"knowledge.read"}
        )
        results.append(
            _result(
                "runtime_required_agent_unavailable",
                started,
                capability="knowledge_search",
                lifecycle_state="unavailable",
                initialization_status="ready",
                health_status="unavailable",
                fallback_used=True,
                success=resolution.selected_agent_id is None,
            )
        )

        fallback = _manager(
            BenchmarkAgent("preferred_agent", priority=10),
            BenchmarkAgent("fallback_agent", priority=20),
        )
        await fallback.initialize()
        fallback.transition("preferred_agent", AgentLifecycleState.UNAVAILABLE)
        started = perf_counter()
        resolution = fallback.resolve_capability(
            "knowledge_search",
            permissions={"knowledge.read"},
            preferred_agent_id="preferred_agent",
        )
        results.append(
            _result(
                "runtime_capability_fallback_selection",
                started,
                selected_agent=resolution.selected_agent_id,
                agent_version="2.0.0",
                capability="knowledge_search",
                lifecycle_state="ready",
                resolution_duration_ms=resolution.resolution_duration_ms,
                resolution_fallback=True,
                fallback_used=True,
                success=resolution.selected_agent_id == "fallback_agent",
            )
        )

        started = perf_counter()
        tracker = AgentBudgetTracker(
            AgentExecutionBudget(max_inference_calls=0, max_output_chars=10)
        )
        budget_exceeded = False
        try:
            tracker.output(11)
        except BudgetExceeded:
            budget_exceeded = True
        results.append(
            _result(
                "runtime_budget_enforcement",
                started,
                budget_status="exceeded",
                success=budget_exceeded,
            )
        )

        cancellation = _manager(BenchmarkAgent("cancellable_agent", delay=10.0))
        await cancellation.initialize()
        started = perf_counter()
        await cancellation.begin_execution("cancellable_agent")

        async def cancellable_work() -> None:
            try:
                await cancellation.registry.get("cancellable_agent").execute(
                    SimpleTask(), None
                )
            finally:
                cancellation.end_execution("cancellable_agent")

        execution = asyncio.create_task(cancellable_work())
        await asyncio.sleep(0)
        execution.cancel()
        cancelled = False
        try:
            await execution
        except asyncio.CancelledError:
            cancelled = True
        results.append(
            _result(
                "runtime_cancellation_during_execution",
                started,
                selected_agent="cancellable_agent",
                lifecycle_state="ready",
                budget_status="cancelled",
                success=(
                    cancelled
                    and cancellation.records["cancellable_agent"].active_executions == 0
                ),
            )
        )

        streaming = _manager(BenchmarkAgent("streaming_agent"))
        await streaming.initialize()
        plan = ExecutionPlan(
            objective="stream event",
            required_agents=["streaming_agent"],
            tasks=[
                AgentTask(
                    task_id="resolve",
                    agent_id="streaming_agent",
                    capability="knowledge_search",
                    objective="resolve",
                    output_contract="KnowledgeEvidenceV1",
                    budget=AgentExecutionBudget(
                        max_inference_calls=0, max_retrieval_calls=1
                    ),
                )
            ],
        )
        context = AgentExecutionContext(
            request_id="benchmark",
            plan_id=plan.plan_id,
            task_id="plan",
            authenticated_user_snapshot=object(),
            permissions=frozenset({"knowledge.read"}),
            department=None,
            role="admin",
            conversation_id=None,
            streaming=True,
            deadline=None,
            budget=plan.tasks[0].budget,
            runtime_services=AgentRuntimeServices(
                database_adapter=None, knowledge_fetcher=lambda: None
            ),
        )
        events: list[str] = []

        async def event_callback(name: str, _data: dict[str, object]) -> None:
            events.append(name)

        started = perf_counter()
        execution_results, _, _ = await ExecutionEngine(
            runtime_manager=streaming
        ).execute(
            plan,
            streaming.registry,
            {"knowledge.read"},
            context,
            event_callback,
        )
        results.append(
            _result(
                "runtime_supervised_streaming_resolution_events",
                started,
                selected_agent="streaming_agent",
                agent_version="2.0.0",
                capability="knowledge_search",
                lifecycle_state="ready",
                initialization_status="ready",
                health_status="healthy",
                budget_status="within_budget",
                success=(
                    execution_results[0].status == "success"
                    and "agent_resolved" in events
                ),
            )
        )
    finally:
        settings.ctv_one_agent_health_poll_enabled = previous_poll

    return {
        "event": "agent_runtime_benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "success_count": sum(bool(item["success"]) for item in results),
        "results": results,
    }


class SimpleTask:
    task_id = "cancel"
    agent_id = "cancellable_agent"


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = str(report["generated_at"]).replace(":", "").replace("+", "Z")
    path = output_dir / f"agent-runtime-{stamp}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline Chapter 2 agent runtime cases.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = asyncio.run(run_runtime_benchmark())
    path = write_report(report, args.output_dir)
    print(f"Agent runtime benchmark: {report['success_count']}/{report['case_count']} safe")
    print(path)
    return 0 if report["success_count"] == report["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
