from __future__ import annotations

import asyncio
import json
import re
from uuid import uuid4

from app.core.config import settings
from app.agents.errors import AgentErrorCategory, AgentRuntimeError
from app.agents.models import AgentExecutionBudget
from app.services.inference_queue import inference_queue
from app.services.ollama_service import ollama_service
from app.supervisor.agent_registry import AgentRegistry, AgentRegistryError
from app.supervisor.permissions import capability_allowed
from app.supervisor.schemas import (
    AgentTask,
    ExecutionPlan,
    RequestedSupervisorMode,
    SupervisorRequest,
)


class SupervisorPlanError(ValueError):
    category = "supervisor_plan_invalid"


REASONING_TERMS = {
    "compare", "recommend", "recommendation", "risk", "risks", "tradeoff",
    "tradeoffs", "analyze", "analysis", "against", "management brief",
    "executive summary", "action plan",
}
KNOWLEDGE_TERMS = {
    "policy", "policies", "guideline", "guidelines", "document", "manual",
    "sop", "knowledge", "equipment", "brand", "production policy",
}
OPERATIONS_TERMS = {
    "task", "tasks", "overdue", "priority", "priorities", "monday",
    "operations", "operational", "project", "projects", "workload", "status",
}
EMPLOYEE_TERMS = {
    "my role", "my responsibilities", "my workload", "employee", "responsibilities",
    "role context", "department",
}


def _contains(question: str, terms: set[str]) -> bool:
    normalized = re.sub(r"\s+", " ", question.lower())
    return any(term in normalized for term in terms)


def requested_domains(question: str, requirements) -> set[str]:
    domains: set[str] = set()
    if requirements.include_knowledge or _contains(question, KNOWLEDGE_TERMS):
        domains.add("knowledge")
    if requirements.include_operations or _contains(question, OPERATIONS_TERMS):
        domains.add("operations")
    if requirements.include_employee or _contains(question, EMPLOYEE_TERMS):
        domains.add("employee")
    return domains


def select_mode(
    question: str,
    requirements,
    requested_mode: RequestedSupervisorMode,
) -> tuple[str, set[str], bool]:
    domains = requested_domains(question, requirements)
    needs_reasoning = _contains(question, REASONING_TERMS)
    if requested_mode == "auto":
        requested_mode = settings.ctv_one_supervisor_default_mode
    if not settings.ctv_one_supervisor_enabled or requested_mode == "direct":
        return "direct", domains, needs_reasoning
    if requested_mode == "supervised":
        return "supervised", domains, needs_reasoning
    supervised = len(domains) >= 2 or (needs_reasoning and bool(domains))
    return ("supervised" if supervised else "direct"), domains, needs_reasoning


def deterministic_plan(
    domains: set[str],
    needs_reasoning: bool,
) -> ExecutionPlan | None:
    if not domains:
        return None
    tasks: list[AgentTask] = []
    agent_by_domain = {
        "knowledge": ("knowledge_agent", "evidence_retrieval", "KnowledgeEvidenceV1"),
        "operations": ("operations_agent", "operations_status", "OperationsSnapshotEvidenceV1"),
        "employee": ("employee_agent", "employee_context", "EmployeeSelfContextV1"),
    }
    for domain in sorted(domains):
        agent_id, capability, contract = agent_by_domain[domain]
        tasks.append(
            AgentTask(
                task_id=f"retrieve_{domain}",
                agent_id=agent_id,
                capability=capability,
                objective=f"Retrieve validated {domain} context.",
                timeout_seconds=settings.ctv_one_supervisor_task_timeout_seconds,
                output_contract=contract,
            )
        )
    source_ids = [task.task_id for task in tasks]
    if needs_reasoning:
        tasks.append(
            AgentTask(
                task_id="reason_over_evidence",
                agent_id="reasoning_agent",
                capability="recommend",
                objective="Compare and synthesize validated evidence.",
                dependency_ids=source_ids,
                timeout_seconds=settings.ctv_one_supervisor_task_timeout_seconds,
                optional=True,
                output_contract="ReasoningSummaryV1",
            )
        )
    tasks.append(
        AgentTask(
            task_id="compose_response",
            agent_id="response_composer_agent",
            capability="final_answer",
            objective="Compose the final grounded Company Brain response.",
            dependency_ids=[task.task_id for task in tasks],
            timeout_seconds=settings.ctv_one_supervisor_task_timeout_seconds,
            output_contract="CompanyBrainAnswerV1",
        )
    )
    return ExecutionPlan(
        objective="Answer a bounded composite enterprise request.",
        tasks=tasks,
        required_agents=list(dict.fromkeys(task.agent_id for task in tasks)),
        estimated_complexity="complex" if needs_reasoning or len(domains) > 2 else "moderate",
    )


def plan_depth(plan: ExecutionPlan) -> int:
    tasks = {task.task_id: task for task in plan.tasks}
    visiting: set[str] = set()
    memo: dict[str, int] = {}

    def depth(task_id: str) -> int:
        if task_id in visiting:
            raise SupervisorPlanError("Circular task dependency.")
        if task_id in memo:
            return memo[task_id]
        visiting.add(task_id)
        task = tasks[task_id]
        value = 1 + max((depth(dep) for dep in task.dependency_ids), default=0)
        visiting.remove(task_id)
        memo[task_id] = value
        return value

    return max((depth(task_id) for task_id in tasks), default=0)


def validate_plan(
    plan: ExecutionPlan,
    registry: AgentRegistry,
    permissions: set[str],
) -> ExecutionPlan:
    if not plan.tasks:
        raise SupervisorPlanError("Plan must contain at least one task.")
    if len(plan.tasks) > settings.ctv_one_supervisor_max_tasks:
        raise SupervisorPlanError("Plan exceeds the configured task limit.")
    tasks = {task.task_id: task for task in plan.tasks}
    if len(tasks) != len(plan.tasks):
        raise SupervisorPlanError("Duplicate task IDs are not permitted.")
    task_agents = set(task.agent_id for task in plan.tasks)
    if set(plan.required_agents) != task_agents:
        raise SupervisorPlanError("Plan agent declarations do not match its tasks.")
    for task in plan.tasks:
        if task.timeout_seconds > settings.ctv_one_supervisor_task_timeout_seconds:
            raise SupervisorPlanError("Plan task timeout exceeds the configured limit.")
        if any(dependency not in tasks for dependency in task.dependency_ids):
            raise SupervisorPlanError("Plan contains an unknown dependency.")
        try:
            agent = registry.get(task.agent_id)
        except AgentRegistryError as exc:
            raise SupervisorPlanError("Plan selected an unknown agent.") from exc
        if not agent.definition.enabled or task.capability not in agent.definition.capabilities:
            raise SupervisorPlanError("Plan selected an unavailable capability.")
        if task.output_contract != agent.definition.output_schema:
            raise SupervisorPlanError("Plan selected an invalid output contract.")
        if not agent.definition.required_permissions.issubset(permissions):
            raise SupervisorPlanError("Plan selected an unauthorized agent.")
        if not capability_allowed(task.capability, permissions):
            raise SupervisorPlanError("Plan selected an unauthorized capability.")
    if plan_depth(plan) > settings.ctv_one_supervisor_max_depth:
        raise SupervisorPlanError("Plan exceeds the configured dependency depth.")
    return plan


def resolve_plan_capabilities(
    plan: ExecutionPlan,
    runtime_manager,
    permissions: set[str],
    *,
    department: str | None = None,
    role: str | None = None,
) -> ExecutionPlan:
    """Resolve every task deterministically without invoking a model."""
    if runtime_manager.initialized_at is None:
        return plan
    resolved_tasks: list[AgentTask] = []
    excluded_optional: set[str] = set()
    system_maximum = AgentExecutionBudget(
        timeout_seconds=settings.ctv_one_supervisor_task_timeout_seconds,
        max_inference_calls=settings.ctv_one_agent_default_max_inference_calls,
        max_retrieval_calls=settings.ctv_one_agent_default_max_retrieval_calls,
        max_evidence_items=settings.ctv_one_agent_default_max_evidence_items,
        max_output_chars=settings.ctv_one_agent_default_max_output_chars,
        max_queue_wait_seconds=settings.ctv_one_agent_default_max_queue_wait_seconds,
    )
    for task in plan.tasks:
        resolution = runtime_manager.resolve_capability(
            task.capability,
            permissions=permissions,
            department=department,
            role=role,
            preferred_agent_id=task.agent_id,
        )
        if not resolution.selected_agent_id:
            if task.optional:
                excluded_optional.add(task.task_id)
                continue
            raise AgentRuntimeError(AgentErrorCategory.UNAVAILABLE)
        definition = runtime_manager.registry.get(resolution.selected_agent_id).definition
        requested_budget = task.budget or definition.default_budget.model_copy(
            update={"timeout_seconds": min(task.timeout_seconds, definition.max_timeout_seconds)}
        )
        resolved_tasks.append(
            task.model_copy(
                update={
                    "agent_id": resolution.selected_agent_id,
                    "agent_version": definition.version,
                    "contract_version": definition.contract_version,
                    "capability_version": "1.0",
                    "budget": requested_budget.bounded_by(system_maximum),
                }
            )
        )
    if excluded_optional:
        resolved_tasks = [
            task.model_copy(
                update={
                    "dependency_ids": [
                        item for item in task.dependency_ids if item not in excluded_optional
                    ]
                }
            )
            for task in resolved_tasks
        ]
    return plan.model_copy(
        update={
            "tasks": resolved_tasks,
            "required_agents": list(dict.fromkeys(task.agent_id for task in resolved_tasks)),
        }
    )


async def llm_plan(
    request: SupervisorRequest,
    registry: AgentRegistry,
    instrumentation=None,
) -> ExecutionPlan:
    if not settings.ctv_one_supervisor_llm_planning_enabled:
        raise SupervisorPlanError("LLM planning is disabled.")
    allowed = [
        {
            "agent_id": item.agent_id,
            "capabilities": sorted(item.capabilities),
        }
        for item in registry.definitions(enabled_only=True)
        if item.required_permissions.issubset(request.permissions)
    ]
    admission = await inference_queue.submit(
        request_id=request.request_id,
        user_id=request.user_id,
        model_name=settings.ctv_one_model_reasoning or settings.ollama_model,
        model_role="reasoning",
        streaming=False,
        estimated_cost_class="reasoning",
    )
    inference_queue.record_result(instrumentation, admission.initial_result)
    lease = await admission.wait()
    inference_queue.record_lease(instrumentation, lease)
    try:
        async with asyncio.timeout(settings.ctv_one_supervisor_planner_timeout_seconds):
            response = await ollama_service.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "Return one strict JSON ExecutionPlan only. Use only listed agents "
                            "and capabilities. "
                            "Create no code, tools, recursive calls, or external actions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "request": request.question,
                                "allowed_agents": allowed,
                                "max_tasks": settings.ctv_one_supervisor_max_tasks,
                                "max_depth": settings.ctv_one_supervisor_max_depth,
                            },
                            ensure_ascii=True,
                        ),
                    },
                ],
                model=settings.ctv_one_model_reasoning or settings.ollama_model,
            )
    except TimeoutError as exc:
        raise SupervisorPlanError("Planner timed out.") from exc
    finally:
        await lease.release()
    cleaned = response.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        payload = json.loads(cleaned)
        payload["plan_id"] = payload.get("plan_id") or str(uuid4())
        payload["mode"] = "supervised"
        payload["planner_type"] = "llm"
        payload["planner_version"] = "v2-c1-llm"
        plan = ExecutionPlan.model_validate(payload)
    except (ValueError, TypeError, KeyError) as exc:
        raise SupervisorPlanError("Planner returned an invalid plan.") from exc
    return validate_plan(plan, registry, request.permissions)
