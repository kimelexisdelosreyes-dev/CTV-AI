import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.supervisor.agent_registry import AgentRegistry
from app.supervisor.execution_engine import ExecutionEngine
from app.supervisor.schemas import AgentDefinition, AgentResult, AgentTask, ExecutionPlan


class FakeAgent:
    definition = AgentDefinition(
        agent_id="fake_agent",
        name="Fake Agent",
        description="Test-only read agent.",
        capabilities=frozenset({"knowledge_search"}),
        supported_intents=frozenset({"policy"}),
        required_permissions=frozenset({"knowledge.read"}),
        input_schema="TestInputV1",
        output_schema="TestOutputV1",
        estimated_cost_class="light",
    )

    def __init__(self):
        self.started = []
        self.current = 0
        self.peak = 0

    async def execute(self, task, _context):
        self.started.append(task.task_id)
        self.current += 1
        self.peak = max(self.peak, self.current)
        try:
            if task.inputs.get("fail"):
                raise RuntimeError("safe failure")
            if task.inputs.get("wait"):
                await asyncio.sleep(task.inputs["wait"])
            return AgentResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                status="success",
                structured_output={"ok": True},
            )
        finally:
            self.current -= 1


class MalformedComposerAgent:
    definition = AgentDefinition(
        agent_id="malformed_composer",
        name="Malformed Composer",
        description="Returns a malformed known contract.",
        capabilities=frozenset({"final_answer"}),
        supported_intents=frozenset({"general"}),
        required_permissions=frozenset({"compose.use"}),
        input_schema="TestInputV1",
        output_schema="CompanyBrainAnswerV1",
        estimated_cost_class="light",
    )

    async def execute(self, task, _context):
        return AgentResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            status="success",
            structured_output={"unexpected": "value"},
        )


def plan(*tasks):
    return ExecutionPlan(objective="test", tasks=list(tasks), required_agents=["fake_agent"])


def task(task_id, *, dependencies=None, optional=False, inputs=None, timeout=1.0):
    return AgentTask(
        task_id=task_id,
        agent_id="fake_agent",
        capability="knowledge_search",
        objective="test",
        dependency_ids=dependencies or [],
        optional=optional,
        inputs=inputs or {},
        timeout_seconds=timeout,
        output_contract="TestOutputV1",
    )


@pytest.mark.asyncio
async def test_dependency_order_parallelism_and_duplicate_prevention(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_max_parallel_tasks", 2)
    registry = AgentRegistry()
    agent = FakeAgent()
    registry.register(agent)
    results, peak, _ = await ExecutionEngine().execute(
        plan(
            task("a", inputs={"wait": 0.02}),
            task("b", inputs={"wait": 0.02}),
            task("c", dependencies=["a", "b"]),
        ),
        registry,
        {"knowledge.read"},
        SimpleNamespace(),
    )
    assert [result.task_id for result in results] == ["a", "b", "c"]
    assert agent.started.count("c") == 1
    assert agent.started.index("c") > agent.started.index("b")
    assert peak == agent.peak == 2


@pytest.mark.asyncio
async def test_required_failure_skips_dependent_but_optional_failure_allows_it() -> None:
    registry = AgentRegistry()
    agent = FakeAgent()
    registry.register(agent)
    required_results, _, _ = await ExecutionEngine().execute(
        plan(task("a", inputs={"fail": True}), task("b", dependencies=["a"])),
        registry,
        {"knowledge.read"},
        SimpleNamespace(),
    )
    assert [result.status for result in required_results] == ["failed", "skipped"]

    optional_results, _, _ = await ExecutionEngine().execute(
        plan(task("a", inputs={"fail": True}, optional=True), task("b", dependencies=["a"])),
        registry,
        {"knowledge.read"},
        SimpleNamespace(),
    )
    assert [result.status for result in optional_results] == ["failed", "success"]


@pytest.mark.asyncio
async def test_malformed_known_output_contract_is_rejected_safely() -> None:
    registry = AgentRegistry()
    registry.register(MalformedComposerAgent())
    malformed_plan = ExecutionPlan(
        objective="test",
        required_agents=["malformed_composer"],
        tasks=[
            AgentTask(
                task_id="compose",
                agent_id="malformed_composer",
                capability="final_answer",
                objective="test",
                output_contract="CompanyBrainAnswerV1",
            )
        ],
    )
    results, _, _ = await ExecutionEngine().execute(
        malformed_plan,
        registry,
        {"compose.use"},
        SimpleNamespace(),
    )
    assert results[0].status == "failed"
    assert results[0].error_category == "supervisor_agent_failed"


@pytest.mark.asyncio
async def test_task_and_total_timeouts_are_bounded(monkeypatch) -> None:
    registry = AgentRegistry()
    registry.register(FakeAgent())
    task_results, _, _ = await ExecutionEngine().execute(
        plan(task("slow", inputs={"wait": 0.1}, timeout=0.01)),
        registry,
        {"knowledge.read"},
        SimpleNamespace(),
    )
    assert task_results[0].status == "timed_out"
    assert task_results[0].error_category == "supervisor_task_timeout"

    monkeypatch.setattr(settings, "ctv_one_supervisor_total_timeout_seconds", 0.01)
    total_results, _, _ = await ExecutionEngine().execute(
        plan(task("slow", inputs={"wait": 0.1}, timeout=1.0)),
        registry,
        {"knowledge.read"},
        SimpleNamespace(),
    )
    assert total_results[0].error_category == "supervisor_total_timeout"
