import logging
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import knowledge as knowledge_route
from app.db.models.employee import DetailLevel, ExperienceLevel, ResponseStyle
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app
from app.schemas.context import ContextMetadata
from app.services import context_engine as context_engine_module
from app.services import operations_context_service as operations_context_module
from app.services.knowledge_service import answer_with_knowledge
from app.services.performance_instrumentation import AskPerformanceInstrumentation


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def user() -> User:
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        password_hash="not-used",
        role=UserRole.employee,
    )


@pytest.mark.anyio
async def test_non_operational_question_does_not_fetch_monday(monkeypatch) -> None:
    async def fake_profile(*_):
        return SimpleNamespace(
            job_title=None,
            experience_level=ExperienceLevel.intermediate,
            primary_responsibilities=None,
            specialties=None,
            preferred_language="English",
            response_style=ResponseStyle.concise,
            detail_level=DetailLevel.standard,
        )

    async def fake_preferences(*_):
        return SimpleNamespace(
            prefers_checklists=True,
            prefers_visual_examples=False,
            comfortable_with_technical_terms=True,
            preferred_output_format="bullets",
            requires_approval_for=None,
            custom_instructions=None,
        )

    async def empty_list(*_):
        return []

    async def fail_monday_fetch(*_):
        raise AssertionError("monday.com should not be fetched")

    monkeypatch.setattr(
        context_engine_module.employee_service,
        "ensure_profile",
        fake_profile,
    )
    monkeypatch.setattr(
        context_engine_module.employee_service,
        "ensure_preferences",
        fake_preferences,
    )
    monkeypatch.setattr(
        context_engine_module.employee_service,
        "list_skills",
        empty_list,
    )
    monkeypatch.setattr(
        context_engine_module.employee_service,
        "list_tools",
        empty_list,
    )
    monkeypatch.setattr(
        context_engine_module.employee_service,
        "list_memories",
        empty_list,
    )
    monkeypatch.setattr(
        context_engine_module.connector_manager,
        "descriptors",
        lambda: [],
    )
    monkeypatch.setattr(
        operations_context_module.connector_manager,
        "tasks",
        fail_monday_fetch,
    )
    monkeypatch.setattr(
        operations_context_module.connector_manager,
        "projects",
        fail_monday_fetch,
    )

    instrumentation = AskPerformanceInstrumentation()
    answer, sources, personalization = await answer_with_knowledge(
        question="Tell me about CTV ONE.",
        top_k=5,
        category=None,
        assistant="general",
        use_employee_context=True,
        current_user=user(),
        db=None,
        instrumentation=instrumentation,
    )

    assert answer == "I could not find relevant approved company knowledge for this request."
    assert sources == []
    assert personalization.operational_context_applied is False
    assert personalization.operational_tasks_used == 0
    assert instrumentation.routed_intent == "general"
    assert instrumentation.operational_task_count == 0


def test_ask_response_schema_remains_unchanged(monkeypatch, caplog) -> None:
    async def fake_current_user():
        return user()

    async def fake_db():
        yield object()

    async def fake_answer_with_knowledge(**kwargs):
        instrumentation = kwargs["instrumentation"]
        instrumentation.record_route("general", 0.45, [])
        instrumentation.answer_character_count = len("do not log answer text")
        return (
            "do not log answer text",
            [],
            ContextMetadata(routed_intent="general", routing_confidence=0.45),
        )

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(
        knowledge_route,
        "answer_with_knowledge",
        fake_answer_with_knowledge,
    )
    caplog.set_level(logging.INFO, logger="app.api.routes.knowledge")

    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask",
            json={"question": "do not log prompt text"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"answer", "sources", "personalization"}
    assert set(body["personalization"]) == {
        "applied",
        "job_title",
        "experience_level",
        "preferred_language",
        "response_style",
        "detail_level",
        "skills_used",
        "tools_used",
        "memories_used",
        "operational_context_applied",
        "operational_tasks_used",
        "operational_boards_used",
        "operational_summary",
        "routed_intent",
        "routing_confidence",
        "routed_collections",
        "intelligence_sources",
    }
    assert "do not log prompt text" not in caplog.text
    assert "do not log answer text" not in caplog.text
