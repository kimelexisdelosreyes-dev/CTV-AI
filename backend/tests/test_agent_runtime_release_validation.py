import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.agents.errors import AgentErrorCategory, AgentRuntimeError
from app.core.config import settings
from app.services.inference_queue import InferenceQueueError
from app.supervisor import agents as agent_module
from app.supervisor.agents import (
    AgentExecutionContext,
    ResponseComposerAgent,
    bounded_composition_context,
    invoke_agent_model,
)
from app.supervisor.planner import deterministic_plan
from app.supervisor.schemas import AgentTask


def _context(instrumentation=None):
    return AgentExecutionContext(
        user=SimpleNamespace(id="user-1"),
        db=None,
        question="Summarize current status from approved sources.",
        top_k=5,
        route=None,
        requirements=None,
        instrumentation=instrumentation,
        knowledge_fetcher=None,
    )


@pytest.mark.asyncio
async def test_queue_wait_timeout_is_distinct_from_inference_timeout(monkeypatch) -> None:
    class Admission:
        initial_result = SimpleNamespace()

        async def wait(self):
            raise InferenceQueueError("queue_wait_timeout", status_code=503)

    class Queue:
        async def submit(self, **_kwargs):
            return Admission()

        @staticmethod
        def record_result(*_args):
            return None

        @staticmethod
        def record_lease(*_args):
            return None

    async def model_must_not_run(*_args, **_kwargs):
        raise AssertionError("Ollama must not run after queue timeout")

    monkeypatch.setattr(agent_module, "inference_queue", Queue())
    monkeypatch.setattr(agent_module.ollama_service, "chat", model_must_not_run)
    with pytest.raises(AgentRuntimeError) as captured:
        await invoke_agent_model(
            messages=[{"role": "user", "content": "safe"}],
            model_name="test",
            model_role="balanced",
            agent_id="response_composer_agent",
            inference_timeout_seconds=0.1,
            context=_context(),
        )
    assert captured.value.category == AgentErrorCategory.QUEUE_TIMEOUT


@pytest.mark.asyncio
async def test_inference_timeout_releases_lease_without_double_counting_queue(monkeypatch) -> None:
    released = []

    class Lease:
        result = SimpleNamespace(wait_duration_ms=7.0)

        async def release(self, *, cancelled=False):
            released.append(cancelled)

    class Admission:
        initial_result = SimpleNamespace()

        async def wait(self):
            return Lease()

    class Queue:
        async def submit(self, **_kwargs):
            return Admission()

        @staticmethod
        def record_result(*_args):
            return None

        @staticmethod
        def record_lease(*_args):
            return None

    async def slow_model(*_args, **_kwargs):
        await asyncio.sleep(1)

    monkeypatch.setattr(agent_module, "inference_queue", Queue())
    monkeypatch.setattr(agent_module.ollama_service, "chat", slow_model)
    with pytest.raises(AgentRuntimeError) as captured:
        await invoke_agent_model(
            messages=[{"role": "user", "content": "safe"}],
            model_name="test",
            model_role="balanced",
            agent_id="response_composer_agent",
            inference_timeout_seconds=0.01,
            context=_context(),
        )
    assert captured.value.category == AgentErrorCategory.EXECUTION_TIMEOUT
    assert released == [False]


def test_deterministic_plan_uses_role_specific_timeouts() -> None:
    plan = deterministic_plan({"knowledge", "operations"}, True)
    assert plan is not None
    timeouts = {task.agent_id: task.timeout_seconds for task in plan.tasks}
    assert timeouts["knowledge_agent"] == settings.ctv_one_supervisor_task_timeout_seconds
    assert timeouts["reasoning_agent"] == settings.ctv_one_agent_reasoning_timeout_seconds
    assert timeouts["response_composer_agent"] == settings.ctv_one_agent_composer_timeout_seconds


def test_composition_context_is_structurally_bounded_and_keeps_citations() -> None:
    results = [
        {
            "agent_id": "knowledge_agent",
            "structured_output": {"source_count": 20, "facts": ["x" * 5000]},
            "evidence": [
                {
                    "evidence_id": f"source-{index}",
                    "citation": f"[Source {index}]",
                    "source_type": "knowledge",
                    "content": "e" * 3000,
                }
                for index in range(20)
            ],
            "warnings": ["warning" * 100],
        },
        {
            "agent_id": "reasoning_agent",
            "structured_output": {"analysis": "r" * 10000},
            "evidence": [],
            "warnings": [],
        },
    ]
    payload = bounded_composition_context("Compare approved findings", results)
    serialized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    assert len(serialized) <= settings.ctv_one_agent_composition_max_total_chars
    assert len(payload["evidence"]) <= settings.ctv_one_agent_composition_max_evidence_items
    assert payload["evidence"][0]["citation"] == "[Source 0]"
    assert payload["findings"] and payload["recommendations"]


@pytest.mark.asyncio
async def test_simple_retrieval_composition_uses_deterministic_fast_path(monkeypatch) -> None:
    async def model_must_not_run(**_kwargs):
        raise AssertionError("Simple composition must not call the model")

    monkeypatch.setattr(agent_module, "invoke_agent_model", model_must_not_run)
    task = AgentTask(
        task_id="compose",
        agent_id="response_composer_agent",
        capability="final_answer",
        objective="status",
        output_contract="CompanyBrainAnswerV1",
        inputs={
            "dependency_results": [
                {
                    "agent_id": "knowledge_agent",
                    "structured_output": {"source_count": 1, "facts": ["approved"]},
                    "evidence": [
                        {
                            "evidence_id": "one",
                            "citation": "[Source 1]",
                            "source_type": "knowledge",
                            "content": "Approved fact.",
                        }
                    ],
                    "warnings": [],
                }
            ]
        },
    )
    result = await ResponseComposerAgent().execute(task, _context())
    assert result.composition_strategy == "deterministic"
    assert "[Source 1]" in result.structured_output["answer"]

