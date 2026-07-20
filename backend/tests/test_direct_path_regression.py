import json
import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routes import knowledge as knowledge_route
from app.core.config import settings
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app
from app.schemas.context import ContextBundle, ContextMetadata
from app.schemas.knowledge import KnowledgeSource
from app.services import context_retrieval_coordinator as retrieval_module
from app.services import knowledge_service
from app.services.model_router import ModelRoutingDecision
from app.services.ollama_service import OllamaStreamEvent
from app.services.operations_context_service import OperationsContext
from app.services.semantic_cache import SemanticCacheResult
from app.supervisor.service import SupervisorOutcome


class TrackingSession(AsyncSession):
    def __init__(self) -> None:
        super().__init__()
        self.rollback_count = 0
        self.usable = True

    def in_transaction(self):
        return True

    async def rollback(self) -> None:
        self.rollback_count += 1
        self.usable = True


def authenticated_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="direct-regression@example.com",
        full_name="Direct Regression User",
        password_hash="unused",
        role=UserRole.employee,
    )


def configure_authenticated_pipeline(monkeypatch, persisted: list[str]) -> None:
    async def build_lookup(**_):
        return None

    async def lookup(_):
        return SemanticCacheResult(skip_reason="test_forced_miss")

    async def store(**_):
        return False

    async def operations(*_, **__):
        return OperationsContext(
            applied=True,
            text="[Monday Task 1] Overdue production edit.",
            task_count=1,
            board_count=1,
            summary="One overdue task",
            original_task_count=1,
            original_chars=40,
            final_chars=40,
        )

    async def employee(*_, **__):
        return ContextBundle(
            system_context="EMPLOYEE CONTEXT\n- Name: Direct Regression User",
            metadata=ContextMetadata(
                applied=True,
                routed_intent="employee",
                intelligence_sources=["employee-context"],
            ),
        )

    async def knowledge(*_, **__):
        return [
            KnowledgeSource(
                document_id="policy-1",
                filename="policy.pdf",
                category="company-policies",
                chunk_index=0,
                page_number=1,
                text="Approved leave policy.",
                score=0.99,
            )
        ]

    async def recent_messages(*_, **__):
        return []

    async def route_model(routing_input):
        role = "operations" if routing_input.include_operations else "fast"
        return ModelRoutingDecision(
            selected_model="qwen3:8b",
            model_role=role,
            routing_reason="direct_regression_test",
            confidence="high",
            complexity="moderate" if routing_input.include_operations else "simple",
            fallback_used=False,
            fallback_reason=None,
            availability_checked=False,
            routing_duration_ms=0.0,
        )

    async def chat(*_, return_metadata=False, **__):
        if return_metadata:
            return "Grounded direct answer.", {"eval_count": 4, "eval_duration": 1_000_000}
        return "Grounded supervised answer."

    async def stream_chat(*_, **__):
        yield OllamaStreamEvent(text="Grounded direct stream.")
        yield OllamaStreamEvent(done=True, metadata={"eval_count": 4})

    async def save_user(*_):
        persisted.append("user")

    async def save_assistant(db, user, *_):
        assert db.usable is True
        assert isinstance(str(user.id), str)
        persisted.append("assistant")

    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    monkeypatch.setattr(knowledge_service.semantic_cache, "build_lookup", build_lookup)
    monkeypatch.setattr(knowledge_service.semantic_cache, "lookup", lookup)
    monkeypatch.setattr(knowledge_service.semantic_cache, "store", store)
    monkeypatch.setattr(
        retrieval_module.operations_context_service,
        "build",
        operations,
    )
    monkeypatch.setattr(retrieval_module.context_engine, "build_employee_context", employee)
    monkeypatch.setattr(retrieval_module.conversation_service, "recent_messages", recent_messages)
    monkeypatch.setattr(knowledge_service, "_search_routed_collections", knowledge)
    monkeypatch.setattr(knowledge_service.model_router, "route", route_model)
    monkeypatch.setattr(knowledge_service.ollama_service, "chat", chat)
    monkeypatch.setattr(knowledge_route.ollama_service, "stream_chat", stream_chat)
    monkeypatch.setattr(knowledge_route, "append_request_user_message", save_user)
    monkeypatch.setattr(
        knowledge_route.conversation_service,
        "append_assistant_message_for_request",
        save_assistant,
    )


@pytest.mark.parametrize(
    ("question", "mode"),
    [
        ("What tasks are overdue?", "auto"),
        ("What tasks are overdue?", "direct"),
        ("What tasks are overdue?", "supervised"),
        ("Based on my role, what should I focus on next?", "auto"),
        ("Based on my role, what should I focus on next?", "direct"),
        ("What is our leave policy?", "direct"),
    ],
)
def test_authenticated_modes_survive_transaction_cleanup_and_persist(
    monkeypatch,
    question,
    mode,
) -> None:
    persisted: list[str] = []
    sessions: list[TrackingSession] = []
    current_user = authenticated_user()

    async def user_override():
        return current_user

    async def db_override():
        session = TrackingSession()
        sessions.append(session)
        try:
            yield session
        finally:
            await session.close()

    configure_authenticated_pipeline(monkeypatch, persisted)
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_db] = db_override
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask",
            json={
                "question": question,
                "supervisor_mode": mode,
                "conversation_id": str(uuid.uuid4()),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["answer"]
    assert persisted == ["user", "assistant"]
    assert sessions[0].usable is True
    assert sessions[0].rollback_count >= 1


def test_direct_metrics_are_json_serializable_primitives(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_supervisor_enabled", True)
    instrumentation = knowledge_service.AskPerformanceInstrumentation()
    knowledge_service.executive_supervisor._record_direct(instrumentation)
    encoded = json.dumps(instrumentation.metrics)
    assert "direct" in encoded


@pytest.mark.asyncio
async def test_fallback_direct_uses_the_same_retrieval_and_inference_pipeline(
    monkeypatch,
) -> None:
    persisted: list[str] = []
    configure_authenticated_pipeline(monkeypatch, persisted)

    async def fallback(**_):
        return SupervisorOutcome(mode="fallback_direct")

    monkeypatch.setattr(
        knowledge_service.executive_supervisor,
        "execute_if_needed",
        fallback,
    )
    instrumentation = knowledge_service.AskPerformanceInstrumentation()
    answer, _, personalization = await knowledge_service.answer_with_knowledge(
        question="What tasks are overdue?",
        top_k=5,
        category=None,
        assistant="general",
        use_employee_context=True,
        current_user=authenticated_user(),
        db=TrackingSession(),
        instrumentation=instrumentation,
        supervisor_mode="supervised",
    )
    assert answer == "Grounded direct answer."
    assert personalization.operational_context_applied is True


def test_direct_operations_stream_protocol_remains_compatible(monkeypatch) -> None:
    persisted: list[str] = []

    async def user_override():
        return authenticated_user()

    async def db_override():
        session = TrackingSession()
        try:
            yield session
        finally:
            await session.close()

    configure_authenticated_pipeline(monkeypatch, persisted)
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_db] = db_override
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask/stream",
            json={"question": "What tasks are overdue?", "supervisor_mode": "direct"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    for event in ("start", "context_ready", "token", "done"):
        assert f"event: {event}" in response.text
    assert "event: error" not in response.text


def test_unexpected_direct_error_is_logged_and_returned_safely(
    monkeypatch,
    caplog,
) -> None:
    async def user_override():
        return authenticated_user()

    async def db_override():
        yield object()

    async def fail_direct(**_):
        raise RuntimeError("diagnostic failure")

    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", fail_direct)
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_db] = db_override
    caplog.set_level(logging.ERROR, logger="ctv_one.knowledge")
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask",
            json={"question": "safe test question", "supervisor_mode": "direct"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.headers["X-Error-Category"] == "ai_request_error"
    assert response.headers["X-Request-ID"] in caplog.text
    assert "Traceback" in caplog.text
    assert "safe test question" not in caplog.text
