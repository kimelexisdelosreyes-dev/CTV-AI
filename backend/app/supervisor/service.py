from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from time import perf_counter

from app.agents.bootstrap import agent_runtime_manager
from app.agents.context import AgentExecutionContext, AgentRuntimeServices
from app.agents.models import AgentExecutionBudget
from app.core.config import settings
from app.supervisor.execution_engine import ExecutionEngine, SupervisorEventCallback
from app.supervisor.permissions import permissions_for_user, snapshot_authenticated_user
from app.supervisor.planner import (
    SupervisorPlanError,
    deterministic_plan,
    llm_plan,
    plan_depth,
    resolve_plan_capabilities,
    select_mode,
    validate_plan,
)
from app.supervisor.schemas import (
    ExecutionPlan,
    RequestedSupervisorMode,
    SupervisorRequest,
    SupervisorResult,
)


@dataclass(frozen=True)
class SupervisorOutcome:
    mode: str
    result: SupervisorResult | None = None
    plan: ExecutionPlan | None = None


class ExecutiveSupervisor:
    def __init__(self) -> None:
        self.runtime_manager = agent_runtime_manager
        self.registry = agent_runtime_manager.registry
        self.engine = ExecutionEngine(runtime_manager=agent_runtime_manager)
        self.active_plans = 0
        self.completed_plans = 0
        self.failed_plans = 0
        self.partial_plans = 0
        self.direct_bypass_count = 0
        self.fallback_count = 0
        self.planning_total_ms = 0.0
        self.execution_total_ms = 0.0
        self.plan_task_total = 0
        self.safe_errors: Counter[str] = Counter()

    async def execute_if_needed(
        self,
        *,
        question: str,
        requested_mode: RequestedSupervisorMode,
        request_id: str,
        conversation_id: str | None,
        streaming: bool,
        route,
        requirements,
        current_user,
        db,
        top_k: int,
        instrumentation,
        knowledge_fetcher,
        event_callback: SupervisorEventCallback | None = None,
    ) -> SupervisorOutcome:
        current_user = snapshot_authenticated_user(current_user)
        total_started = perf_counter()
        mode, domains, needs_reasoning = select_mode(
            question,
            requirements,
            requested_mode,
        )
        self._metric(instrumentation, "supervisor_enabled", settings.ctv_one_supervisor_enabled)
        self._metric(instrumentation, "supervisor_planning_required", mode == "supervised")
        self._metric(instrumentation, "supervisor_cache_hit", False)
        if mode == "direct":
            self.direct_bypass_count += 1
            self._record_direct(instrumentation)
            return SupervisorOutcome(mode="direct")

        permissions = permissions_for_user(current_user)
        request = SupervisorRequest(
            request_id=request_id,
            user_id=str(current_user.id),
            conversation_id=conversation_id,
            question=question,
            permissions=permissions,
            streaming=streaming,
        )
        planning_started = perf_counter()
        planner_type = "deterministic"
        try:
            plan = deterministic_plan(domains, needs_reasoning)
            if plan is None:
                planner_type = "llm"
                plan = await llm_plan(request, self.registry, instrumentation)
            plan = resolve_plan_capabilities(
                plan,
                self.runtime_manager,
                permissions,
                role=current_user.role.value,
            )
            plan = validate_plan(plan, self.registry, permissions)
        except Exception as exc:
            category = getattr(exc, "category", "supervisor_planning_failed")
            self.safe_errors[category] += 1
            self.failed_plans += 1
            self._metric(instrumentation, "supervisor_error_category", category)
            if settings.ctv_one_supervisor_fallback_direct:
                self.fallback_count += 1
                self._metric(instrumentation, "supervisor_fallback_used", True)
                self._metric(instrumentation, "supervisor_mode", "fallback_direct")
                await self._emit(
                    event_callback,
                    "supervisor_mode",
                    {"mode": "fallback_direct", "plan_required": True},
                )
                return SupervisorOutcome(mode="fallback_direct")
            raise SupervisorPlanError("Supervisor planning failed safely.") from exc

        planning_ms = round((perf_counter() - planning_started) * 1000, 3)
        self.planning_total_ms += planning_ms
        self.plan_task_total += len(plan.tasks)
        self._metric(instrumentation, "supervisor_mode", "supervised")
        self._metric(instrumentation, "supervisor_planner_type", planner_type)
        self._metric(instrumentation, "supervisor_plan_task_count", len(plan.tasks))
        self._metric(instrumentation, "supervisor_plan_depth", plan_depth(plan))
        self._metric(instrumentation, "supervisor_agents_selected", plan.required_agents)
        self._metric(instrumentation, "supervisor_planning_duration_ms", planning_ms)
        await self._emit(
            event_callback,
            "supervisor_mode",
            {"mode": "supervised", "plan_required": True},
        )
        await self._emit(
            event_callback,
            "plan_ready",
            {
                "plan_id": plan.plan_id,
                "task_count": len(plan.tasks),
                "agent_types": plan.required_agents,
                "estimated_complexity": plan.estimated_complexity,
            },
        )

        if hasattr(db, "in_transaction") and db.in_transaction():
            await db.rollback()
        maximum_budget = AgentExecutionBudget(
            timeout_seconds=settings.ctv_one_supervisor_task_timeout_seconds,
            max_inference_calls=settings.ctv_one_agent_default_max_inference_calls,
            max_retrieval_calls=settings.ctv_one_agent_default_max_retrieval_calls,
            max_evidence_items=settings.ctv_one_agent_default_max_evidence_items,
            max_output_chars=settings.ctv_one_agent_default_max_output_chars,
            max_queue_wait_seconds=settings.ctv_one_agent_default_max_queue_wait_seconds,
        )
        context = AgentExecutionContext(
            request_id=request_id,
            plan_id=plan.plan_id,
            task_id="plan",
            authenticated_user_snapshot=current_user,
            permissions=frozenset(permissions),
            department=None,
            role=current_user.role.value,
            conversation_id=conversation_id,
            streaming=streaming,
            deadline=None,
            budget=maximum_budget,
            runtime_services=AgentRuntimeServices(
                database_adapter=db,
                knowledge_fetcher=knowledge_fetcher,
                instrumentation=instrumentation,
            ),
            question=question,
            top_k=top_k,
            route=route,
            requirements=requirements,
        )
        self.active_plans += 1
        try:
            results, peak, execution_ms = await self.engine.execute(
                plan,
                self.registry,
                permissions,
                context,
                event_callback,
            )
        finally:
            self.active_plans -= 1
        self.execution_total_ms += execution_ms
        successful = [result for result in results if result.status == "success"]
        failures = [result for result in results if result.status != "success"]
        if failures:
            error_category = failures[0].error_category or "supervisor_agent_failed"
            self.safe_errors[error_category] += 1
            self._metric(instrumentation, "supervisor_error_category", error_category)
        composer = next(
            (result for result in results if result.agent_id == "response_composer_agent"),
            None,
        )
        if composer and composer.status == "success":
            final_answer = str(composer.structured_output.get("answer") or "").strip()
        else:
            final_answer = self._deterministic_summary(successful)
        if not final_answer and settings.ctv_one_supervisor_fallback_direct:
            self.fallback_count += 1
            self.failed_plans += 1
            self._metric(instrumentation, "supervisor_fallback_used", True)
            self._metric(instrumentation, "supervisor_mode", "fallback_direct")
            await self._emit(
                event_callback,
                "supervisor_mode",
                {"mode": "fallback_direct", "plan_required": True},
            )
            return SupervisorOutcome(mode="fallback_direct", plan=plan)
        evidence = []
        seen: set[str] = set()
        evidence_chars = 0
        for result in successful:
            for item in result.evidence:
                if (
                    item.evidence_id not in seen
                    and len(evidence) < 12
                    and evidence_chars < 12000
                ):
                    seen.add(item.evidence_id)
                    evidence_chars += len(item.content)
                    evidence.append(item)
        partial = bool(failures)
        warnings = list(dict.fromkeys(
            warning for result in results for warning in result.warnings
        ))
        metrics = {
            "planner_type": planner_type,
            "task_count": len(plan.tasks),
            "planning_duration_ms": planning_ms,
            "execution_duration_ms": execution_ms,
            "composition_duration_ms": composer.duration_ms if composer else 0.0,
            "parallelism_peak": peak,
            "success_count": len(successful),
            "failure_count": len(failures),
            "timeout_count": sum(result.status == "timed_out" for result in results),
            "agent_versions": {
                result.agent_id: result.agent_version
                for result in results
                if result.agent_version
            },
            "capabilities": [
                result.capability for result in results if result.capability
            ],
            "budget_status": (
                "exceeded"
                if any(
                    result.error_category == "agent_budget_exceeded"
                    for result in results
                )
                else "within_budget"
            ),
            "task_outcomes": [
                ":".join(
                    (
                        result.agent_id,
                        result.status,
                        result.error_category or "none",
                    )
                )
                for result in results
            ],
        }
        supervisor_result = SupervisorResult(
            plan_id=plan.plan_id,
            mode="supervised",
            task_results=results,
            final_answer=final_answer,
            citations=[item.citation for item in evidence],
            warnings=warnings,
            partial=partial,
            metrics=metrics,
        )
        self.completed_plans += 1
        if partial:
            self.partial_plans += 1
        total_ms = round((perf_counter() - total_started) * 1000, 3)
        for name, value in (
            ("supervisor_execution_duration_ms", execution_ms),
            ("supervisor_composition_duration_ms", metrics["composition_duration_ms"]),
            ("supervisor_total_duration_ms", total_ms),
            ("supervisor_parallelism_peak", peak),
            ("supervisor_task_success_count", len(successful)),
            ("supervisor_task_failure_count", len(failures)),
            ("supervisor_task_timeout_count", metrics["timeout_count"]),
            ("supervisor_partial_result", partial),
            ("supervisor_fallback_used", False),
            ("supervisor_direct_bypass", False),
            ("agent_runtime_selected_agents", [result.agent_id for result in results]),
            ("agent_runtime_agent_versions", metrics["agent_versions"]),
            ("agent_runtime_capabilities", metrics["capabilities"]),
            ("agent_runtime_budget_status", metrics["budget_status"]),
            ("agent_runtime_task_outcomes", metrics["task_outcomes"]),
            (
                "agent_runtime_queue_wait_ms",
                round(sum(result.resource_usage.queue_wait_ms for result in results), 3),
            ),
        ):
            self._metric(instrumentation, name, value)
        return SupervisorOutcome(mode="supervised", result=supervisor_result, plan=plan)

    def record_cache_hit(self, instrumentation) -> None:
        self.direct_bypass_count += 1
        self._metric(instrumentation, "supervisor_enabled", settings.ctv_one_supervisor_enabled)
        self._metric(instrumentation, "supervisor_planning_required", False)
        self._record_direct(instrumentation)
        self._metric(instrumentation, "supervisor_cache_hit", True)

    async def status(self) -> dict[str, object]:
        definitions = self.registry.definitions()
        runtime_status = await self.runtime_manager.status()
        unavailable_required = [
            item["agent_id"]
            for item in runtime_status["agents"]
            if item["lifecycle_state"] not in {"ready", "degraded"}
            and self.registry.get(item["agent_id"]).definition.required
        ]
        return {
            "enabled": settings.ctv_one_supervisor_enabled,
            "planner_enabled": settings.ctv_one_supervisor_llm_planning_enabled,
            "registered_agents": self.registry.safe_diagnostics(),
            "enabled_agents": sum(item.enabled for item in definitions),
            "capability_count": len({cap for item in definitions for cap in item.capabilities}),
            "active_plans": self.active_plans,
            "completed_plans": self.completed_plans,
            "failed_plans": self.failed_plans,
            "partial_plans": self.partial_plans,
            "direct_bypass_count": self.direct_bypass_count,
            "fallback_count": self.fallback_count,
            "average_plan_tasks": round(
                self.plan_task_total / self.completed_plans if self.completed_plans else 0.0,
                3,
            ),
            "average_planning_ms": round(
                self.planning_total_ms / max(self.completed_plans + self.failed_plans, 1), 3
            ),
            "average_execution_ms": round(
                self.execution_total_ms / self.completed_plans if self.completed_plans else 0.0,
                3,
            ),
            "recent_safe_error_categories": dict(self.safe_errors),
            "configuration_limits": {
                "max_tasks": settings.ctv_one_supervisor_max_tasks,
                "max_depth": settings.ctv_one_supervisor_max_depth,
                "max_parallel_tasks": settings.ctv_one_supervisor_max_parallel_tasks,
                "planner_timeout_seconds": settings.ctv_one_supervisor_planner_timeout_seconds,
                "task_timeout_seconds": settings.ctv_one_supervisor_task_timeout_seconds,
                "total_timeout_seconds": settings.ctv_one_supervisor_total_timeout_seconds,
            },
            "runtime_ready": not unavailable_required,
            "resolvable_capabilities": runtime_status["available_capability_count"],
            "unavailable_required_agents": unavailable_required,
            "capability_resolution_failures": runtime_status.get("metrics", {}).get(
                "capability_resolution_failure_count", 0
            ),
        }

    @staticmethod
    async def _emit(callback, name: str, data: dict[str, object]) -> None:
        if callback and settings.ctv_one_supervisor_stream_events_enabled:
            await callback(name, data)

    @staticmethod
    def _metric(instrumentation, name: str, value) -> None:
        if instrumentation:
            instrumentation.record_metric(name, value)

    def _record_direct(self, instrumentation) -> None:
        self._metric(instrumentation, "supervisor_mode", "direct")
        self._metric(instrumentation, "supervisor_planner_type", "none")
        self._metric(instrumentation, "supervisor_direct_bypass", True)
        self._metric(instrumentation, "supervisor_fallback_used", False)

    @staticmethod
    def _deterministic_summary(results) -> str:
        parts = []
        for result in results:
            if result.agent_id == "response_composer_agent":
                continue
            text = json.dumps(result.structured_output, ensure_ascii=True)
            parts.append(f"{result.agent_id}: {text[:1800]}")
        if not parts:
            return ""
        return "Partial enterprise result:\n\n" + "\n\n".join(parts)


executive_supervisor = ExecutiveSupervisor()
