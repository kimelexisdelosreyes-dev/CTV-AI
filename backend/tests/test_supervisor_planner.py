from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.supervisor.agents import build_agent_registry
from app.supervisor.cache import supervisor_cache_fingerprint
from app.supervisor.planner import (
    SupervisorPlanError,
    deterministic_plan,
    plan_depth,
    select_mode,
    validate_plan,
)
from app.supervisor.schemas import AgentTask, ExecutionPlan


def requirements(*, knowledge=False, operations=False, employee=False):
    return SimpleNamespace(
        include_knowledge=knowledge,
        include_operations=operations,
        include_employee=employee,
    )


def test_simple_requests_stay_direct_and_length_alone_does_not_plan(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    assert (
        select_mode("What is our leave policy?", requirements(knowledge=True), "auto")[0]
        == "direct"
    )
    assert (
        select_mode("What tasks are overdue?", requirements(operations=True), "auto")[0]
        == "direct"
    )
    long_simple = "Please summarize this approved policy clearly. " * 500
    assert select_mode(long_simple, requirements(knowledge=True), "auto")[0] == "direct"


def test_composite_requests_use_deterministic_supervision(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    mode, domains, reasoning = select_mode(
        "Compare overdue tasks with our production policy and recommend actions.",
        requirements(knowledge=True, operations=True),
        "auto",
    )
    assert mode == "supervised"
    plan = deterministic_plan(domains, reasoning)
    assert plan is not None
    assert plan.planner_type == "deterministic"
    assert {task.agent_id for task in plan.tasks} == {
        "knowledge_agent",
        "operations_agent",
        "reasoning_agent",
        "response_composer_agent",
    }
    assert plan_depth(plan) == 3


def test_forced_modes_are_explicit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    assert select_mode("simple", requirements(), "direct")[0] == "direct"
    assert select_mode("simple", requirements(), "supervised")[0] == "supervised"
    monkeypatch.setattr(settings, "ctv_one_supervisor_default_mode", "direct")
    assert select_mode("Compare operations with policy", requirements(), "auto")[0] == "direct"


def test_plan_rejects_unknown_agent_cycle_limit_and_unauthorized(monkeypatch) -> None:
    registry = build_agent_registry()
    permissions = {
        "knowledge.read",
        "operations.read",
        "employee.self",
        "reasoning.use",
        "compose.use",
    }
    unknown = ExecutionPlan(
        objective="test",
        required_agents=["unknown"],
        tasks=[
            AgentTask(
                task_id="x",
                agent_id="unknown",
                capability="knowledge_search",
                objective="test",
                output_contract="x",
            )
        ],
    )
    with pytest.raises(SupervisorPlanError, match="unknown agent"):
        validate_plan(unknown, registry, permissions)

    circular = ExecutionPlan(
        objective="test",
        required_agents=["knowledge_agent"],
        tasks=[
            AgentTask(
                task_id="a",
                agent_id="knowledge_agent",
                capability="knowledge_search",
                objective="a",
                dependency_ids=["b"],
                output_contract="KnowledgeEvidenceV1",
            ),
            AgentTask(
                task_id="b",
                agent_id="knowledge_agent",
                capability="knowledge_search",
                objective="b",
                dependency_ids=["a"],
                output_contract="KnowledgeEvidenceV1",
            ),
        ],
    )
    with pytest.raises(SupervisorPlanError, match="Circular"):
        validate_plan(circular, registry, permissions)

    monkeypatch.setattr(settings, "ctv_one_supervisor_max_tasks", 1)
    with pytest.raises(SupervisorPlanError, match="task limit"):
        validate_plan(circular, registry, permissions)
    monkeypatch.setattr(settings, "ctv_one_supervisor_max_tasks", 6)

    plan = deterministic_plan({"employee"}, False)
    assert plan is not None
    with pytest.raises(SupervisorPlanError, match="unauthorized"):
        validate_plan(plan, registry, {"compose.use"})


def test_supervisor_cache_fingerprint_tracks_plan_and_source_revisions() -> None:
    registry = build_agent_registry()
    plan = deterministic_plan({"knowledge", "operations"}, False)
    assert plan is not None
    common = {
        "plan": plan,
        "registry": registry,
        "operations_content_hash": "ops-1",
        "employee_scope": None,
    }
    first = supervisor_cache_fingerprint(
        question="  Compare   POLICY with operations  ",
        knowledge_revision="knowledge-1",
        **common,
    )
    normalized = supervisor_cache_fingerprint(
        question="compare policy with OPERATIONS",
        knowledge_revision="knowledge-1",
        **common,
    )
    revised = supervisor_cache_fingerprint(
        question="compare policy with operations",
        knowledge_revision="knowledge-2",
        **common,
    )
    assert first == normalized
    assert first != revised
    assert len(first) == 64
