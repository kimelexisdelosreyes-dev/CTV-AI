import asyncio
from time import perf_counter
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import knowledge as knowledge_route
from app.api.routes import runtime as runtime_route
from app.core.config import settings
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app
from app.schemas.context import ContextMetadata
from app.services import knowledge_service
from app.services.knowledge_service import PreparedKnowledgeAnswer, answer_with_knowledge
from app.services.performance_instrumentation import AskPerformanceInstrumentation
from app.services.semantic_cache import SemanticCacheResult
from app.supervisor.schemas import AgentResult, AgentTask, ExecutionPlan, SupervisorResult
from app.supervisor.service import SupervisorOutcome, executive_supervisor
from app.supervisor import service as supervisor_service_module
from app.supervisor import planner as supervisor_planner_module
from app.supervisor import agents as supervisor_agents_module


def user(role=UserRole.employee):
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        full_name="Supervisor User",
        password_hash="unused",
        role=role,
    )


async def fake_db():
    yield object()


@pytest.mark.asyncio
async def test_semantic_cache_hit_bypasses_supervisor(monkeypatch) -> None:
    async def build_lookup(**_):
        return None

    async def lookup(_):
        return SemanticCacheResult(
            hit=True,
            hit_type="exact",
            answer="Cached direct answer",
            personalization=ContextMetadata(),
        )

    async def forbidden_supervisor(**_):
        raise AssertionError("Supervisor must not run for a cache hit")

    def forbidden_resolution(*_args, **_kwargs):
        raise AssertionError("Runtime resolution must not run for a cache hit")

    async def forbidden_health(*_args, **_kwargs):
        raise AssertionError("Health polling must not run for a cache hit")

    async def forbidden_ollama(*_args, **_kwargs):
        raise AssertionError("Ollama must not run for a cache hit")

    monkeypatch.setattr(knowledge_service.semantic_cache, "build_lookup", build_lookup)
    monkeypatch.setattr(knowledge_service.semantic_cache, "lookup", lookup)
    monkeypatch.setattr(
        knowledge_service.executive_supervisor,
        "execute_if_needed",
        forbidden_supervisor,
    )
    monkeypatch.setattr(
        knowledge_service.executive_supervisor.runtime_manager,
        "resolve_capability",
        forbidden_resolution,
    )
    monkeypatch.setattr(
        knowledge_service.executive_supervisor.runtime_manager,
        "health_check",
        forbidden_health,
    )
    monkeypatch.setattr(
        supervisor_agents_module.ollama_service,
        "chat",
        forbidden_ollama,
    )
    instrumentation = AskPerformanceInstrumentation()
    answer, _, _ = await answer_with_knowledge(
        question="What is our leave policy?",
        top_k=5,
        category=None,
        assistant="general",
        use_employee_context=False,
        current_user=user(),
        db=None,
        instrumentation=instrumentation,
    )
    assert answer == "Cached direct answer"
    assert instrumentation.metrics["supervisor_cache_hit"] is True
    assert instrumentation.metrics["supervisor_direct_bypass"] is True


@pytest.mark.asyncio
async def test_planner_failure_falls_back_to_direct(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_supervisor_fallback_direct", True)

    def fail_plan(*_):
        raise ValueError("raw planner output must not escape")

    monkeypatch.setattr(supervisor_service_module, "deterministic_plan", fail_plan)
    instrumentation = AskPerformanceInstrumentation()
    outcome = await executive_supervisor.execute_if_needed(
        question="Compare overdue tasks with policy.",
        requested_mode="supervised",
        request_id="request-1",
        conversation_id=None,
        streaming=False,
        route=SimpleNamespace(),
        requirements=SimpleNamespace(
            include_knowledge=True,
            include_operations=True,
            include_employee=False,
        ),
        current_user=user(),
        db=object(),
        top_k=5,
        instrumentation=instrumentation,
        knowledge_fetcher=None,
    )
    assert outcome.mode == "fallback_direct"
    assert instrumentation.metrics["supervisor_fallback_used"] is True
    assert "raw planner output" not in str(instrumentation.metrics)


@pytest.mark.asyncio
async def test_runtime_planner_timeout_falls_back_without_task_timeout_delay(
    monkeypatch,
) -> None:
    released = False

    class Lease:
        wait_duration_ms = 0.0
        queue_depth_at_entry = 0
        active_global = 1
        active_for_model = 1
        user_active_count = 1
        model_limit = 1
        priority = "interactive_reasoning"

        async def release(self, **_):
            nonlocal released
            released = True

    class Admission:
        initial_result = SimpleNamespace(
            admitted=True,
            rejected=False,
            queued=False,
            priority="interactive_reasoning",
            queue_position=None,
            queue_depth_at_entry=0,
            wait_duration_ms=0.0,
            rejection_reason=None,
            retry_after_seconds=None,
        )

        async def wait(self):
            return Lease()

    async def submit(**_):
        return Admission()

    async def slow_planner(*_, **__):
        await asyncio.sleep(1)

    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_supervisor_planner_timeout_seconds", 0.01)
    monkeypatch.setattr(supervisor_planner_module.inference_queue, "submit", submit)
    monkeypatch.setattr(
        supervisor_planner_module.inference_queue,
        "record_result",
        lambda *_: None,
    )
    monkeypatch.setattr(
        supervisor_planner_module.inference_queue,
        "record_lease",
        lambda *_: None,
    )
    monkeypatch.setattr(supervisor_planner_module.ollama_service, "chat", slow_planner)
    instrumentation = AskPerformanceInstrumentation()
    started = perf_counter()
    outcome = await executive_supervisor.execute_if_needed(
        question="Prepare the bounded response.",
        requested_mode="supervised",
        request_id="request-timeout",
        conversation_id=None,
        streaming=False,
        route=SimpleNamespace(),
        requirements=SimpleNamespace(
            include_knowledge=False,
            include_operations=False,
            include_employee=False,
        ),
        current_user=user(),
        db=object(),
        top_k=5,
        instrumentation=instrumentation,
        knowledge_fetcher=None,
    )
    elapsed = perf_counter() - started
    assert outcome.mode == "fallback_direct"
    assert elapsed < 0.2
    assert released is True
    assert instrumentation.metrics["supervisor_error_category"] == "supervisor_plan_invalid"


@pytest.mark.asyncio
async def test_llm_planner_is_not_used_for_known_composite_plan(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)

    async def forbidden_llm(*_):
        raise AssertionError("Known composite work must use deterministic planning")

    async def execute(plan, *_):
        return [
            AgentResult(
                task_id="compose_response",
                agent_id="response_composer_agent",
                status="success",
                structured_output={"answer": "Composed"},
            )
        ], 2, 3.0

    monkeypatch.setattr(supervisor_service_module, "llm_plan", forbidden_llm)
    monkeypatch.setattr(executive_supervisor.engine, "execute", execute)
    outcome = await executive_supervisor.execute_if_needed(
        question="Compare overdue tasks with policy.",
        requested_mode="auto",
        request_id="request-deterministic",
        conversation_id=None,
        streaming=False,
        route=SimpleNamespace(),
        requirements=SimpleNamespace(
            include_knowledge=True,
            include_operations=True,
            include_employee=False,
        ),
        current_user=user(),
        db=object(),
        top_k=5,
        instrumentation=AskPerformanceInstrumentation(),
        knowledge_fetcher=None,
    )
    assert outcome.result is not None
    assert outcome.result.metrics["planner_type"] == "deterministic"


@pytest.mark.asyncio
async def test_unknown_forced_flow_uses_constrained_llm_planner(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    called = False
    plan = ExecutionPlan(
        objective="Bounded answer",
        required_agents=["response_composer_agent"],
        planner_type="llm",
        planner_version="test-llm",
        tasks=[
            AgentTask(
                task_id="compose_response",
                agent_id="response_composer_agent",
                capability="final_answer",
                objective="Compose",
                output_contract="CompanyBrainAnswerV1",
            )
        ],
    )

    async def fake_llm(*_):
        nonlocal called
        called = True
        return plan

    async def execute(*_):
        return [
            AgentResult(
                task_id="compose_response",
                agent_id="response_composer_agent",
                status="success",
                structured_output={"answer": "LLM planned"},
            )
        ], 1, 1.0

    monkeypatch.setattr(supervisor_service_module, "llm_plan", fake_llm)
    monkeypatch.setattr(executive_supervisor.engine, "execute", execute)
    outcome = await executive_supervisor.execute_if_needed(
        question="Prepare the bounded response.",
        requested_mode="supervised",
        request_id="request-llm",
        conversation_id=None,
        streaming=False,
        route=SimpleNamespace(),
        requirements=SimpleNamespace(
            include_knowledge=False,
            include_operations=False,
            include_employee=False,
        ),
        current_user=user(),
        db=object(),
        top_k=5,
        instrumentation=AskPerformanceInstrumentation(),
        knowledge_fetcher=None,
    )
    assert called is True
    assert outcome.result is not None
    assert outcome.result.metrics["planner_type"] == "llm"


@pytest.mark.asyncio
async def test_composer_failure_returns_deterministic_partial_result(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)

    async def execute(*_):
        return [
            AgentResult(
                task_id="retrieve_operations",
                agent_id="operations_agent",
                status="success",
                structured_output={"summary": "Two tasks are overdue."},
            ),
            AgentResult(
                task_id="compose_response",
                agent_id="response_composer_agent",
                status="failed",
                error_category="supervisor_agent_failed",
            ),
        ], 1, 1.0

    monkeypatch.setattr(executive_supervisor.engine, "execute", execute)
    outcome = await executive_supervisor.execute_if_needed(
        question="Recommend actions for overdue tasks.",
        requested_mode="supervised",
        request_id="request-partial",
        conversation_id=None,
        streaming=False,
        route=SimpleNamespace(),
        requirements=SimpleNamespace(
            include_knowledge=False,
            include_operations=True,
            include_employee=False,
        ),
        current_user=user(),
        db=object(),
        top_k=5,
        instrumentation=AskPerformanceInstrumentation(),
        knowledge_fetcher=None,
    )
    assert outcome.result is not None
    assert outcome.result.partial is True
    assert outcome.result.metrics["composition_strategy"] == "fallback_deterministic"
    assert outcome.result.final_answer.startswith("Partial enterprise result:")
    assert "Two tasks are overdue" in outcome.result.final_answer


def test_supervised_stream_emits_safe_compatible_lifecycle(monkeypatch) -> None:
    async def current_user():
        return user()

    async def supervised_prepare(**kwargs):
        callback = kwargs["supervisor_event_callback"]
        await callback("supervisor_mode", {"mode": "supervised", "plan_required": True})
        await callback(
            "plan_ready",
            {
                "plan_id": "safe-plan",
                "task_count": 3,
                "agent_types": ["knowledge_agent", "operations_agent"],
                "estimated_complexity": "moderate",
            },
        )
        await callback("agent_started", {"task_id": "k", "agent_id": "knowledge_agent"})
        await callback(
            "agent_completed",
            {
                "task_id": "k",
                "agent_id": "knowledge_agent",
                "status": "success",
                "duration_ms": 1.0,
            },
        )
        return PreparedKnowledgeAnswer(
            messages=[],
            sources=[],
            personalization=ContextMetadata(),
            model_override=None,
            supervised_answer="Safe composed answer",
            supervisor_result=SupervisorResult(
                plan_id="safe-plan",
                mode="supervised",
                task_results=[],
                final_answer="Safe composed answer",
            ),
        )

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", supervised_prepare)
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask/stream",
            json={
                "question": "private composite request",
                "supervisor_mode": "supervised",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    for event in (
        "start",
        "supervisor_mode",
        "plan_ready",
        "agent_started",
        "agent_completed",
        "context_ready",
        "token",
        "done",
    ):
        assert f"event: {event}" in response.text
    assert "Safe composed answer" in response.text
    assert "private composite request" not in response.text
    assert "hidden" not in response.text.lower()


def test_supervisor_diagnostics_require_admin_and_are_safe(monkeypatch) -> None:
    async def employee():
        return user()

    async def admin():
        return user(UserRole.admin)

    async def safe_status():
        return {
            "enabled": True,
            "registered_agents": [{"agent_id": "knowledge_agent"}],
            "active_plans": 0,
        }

    monkeypatch.setattr(runtime_route.executive_supervisor, "status", safe_status)
    app.dependency_overrides[get_current_user] = employee
    try:
        forbidden = TestClient(app).get("/api/v1/runtime/supervisor/status")
        app.dependency_overrides[get_current_user] = admin
        allowed = TestClient(app).get("/api/v1/runtime/supervisor/status")
    finally:
        app.dependency_overrides.clear()
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    serialized = str(allowed.json())
    assert "question" not in serialized
    assert "answer" not in serialized
    assert "employee@example.com" not in serialized
