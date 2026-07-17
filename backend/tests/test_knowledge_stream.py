import uuid

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import knowledge as knowledge_route
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app
from app.schemas.context import ContextMetadata
from app.services.knowledge_service import PreparedKnowledgeAnswer
from app.services.ollama_service import OllamaStreamEvent


def user() -> User:
    return User(
        id=uuid.uuid4(),
        email="stream@example.com",
        full_name="Stream User",
        password_hash="not-used",
        role=UserRole.employee,
    )


async def fake_current_user():
    return user()


async def fake_db():
    yield object()


def test_stream_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/knowledge/ask/stream",
        json={"question": "What is the policy?"},
    )
    assert response.status_code == 401


def test_stream_emits_safe_progressive_events(monkeypatch) -> None:
    async def fake_prepare(**_):
        return PreparedKnowledgeAnswer(
            messages=[{"role": "system", "content": "hidden prompt"}],
            sources=[],
            personalization=ContextMetadata(
                routed_intent="policy", routing_confidence=0.9
            ),
            model_override="routed:test",
        )

    async def fake_stream(*_args, **kwargs):
        assert kwargs["model"] == "routed:test"
        yield OllamaStreamEvent(text="Visible ")
        yield OllamaStreamEvent(text="answer")
        yield OllamaStreamEvent(done=True, metadata={"eval_count": 2})

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", fake_prepare)
    monkeypatch.setattr(knowledge_route.ollama_service, "stream_chat", fake_stream)
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask/stream",
            json={"question": "safe question"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: start" in response.text
    assert "event: context_ready" in response.text
    assert response.text.count("event: token") == 2
    assert "event: done" in response.text
    assert "hidden prompt" not in response.text
    assert "safe question" not in response.text


def test_stream_returns_controlled_error_event(monkeypatch) -> None:
    async def failed_prepare(**_):
        from app.services.ollama_service import OllamaInferenceTimeoutError

        raise OllamaInferenceTimeoutError()

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", failed_prepare)
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask/stream",
            json={"question": "safe question"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "model_inference_timeout" in response.text
    assert "safe question" not in response.text


def test_stream_persists_one_user_and_completed_assistant(monkeypatch) -> None:
    conversation_id = uuid.uuid4()
    client_message_id = uuid.uuid4()
    persisted: list[tuple[str, str]] = []

    async def fake_prepare(**_):
        return PreparedKnowledgeAnswer(
            messages=[{"role": "user", "content": "hidden"}],
            sources=[],
            personalization=ContextMetadata(),
            model_override=None,
        )

    async def fake_stream(*_args, **_kwargs):
        yield OllamaStreamEvent(text="Saved answer")
        yield OllamaStreamEvent(done=True, metadata={})

    async def save_user(*args):
        assert args[-1] == client_message_id
        persisted.append(("user", args[-2]))

    async def save_assistant(*args):
        persisted.append(("assistant", args[-1]))

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", fake_prepare)
    monkeypatch.setattr(knowledge_route.ollama_service, "stream_chat", fake_stream)
    monkeypatch.setattr(
        knowledge_route.conversation_service,
        "append_user_message_for_request",
        save_user,
    )
    monkeypatch.setattr(
        knowledge_route.conversation_service,
        "append_assistant_message_for_request",
        save_assistant,
    )
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask/stream",
            json={
                "question": "Visible question",
                "conversation_id": str(conversation_id),
                "client_message_id": str(client_message_id),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert persisted == [
        ("user", "Visible question"),
        ("assistant", "Saved answer"),
    ]
    assert '"answer_chars":12' in response.text
    assert "event: done" in response.text
    assert "\n\n" in response.text


def test_zero_token_stream_does_not_persist_assistant(monkeypatch) -> None:
    persisted_assistants: list[str] = []

    async def fake_prepare(**_):
        return PreparedKnowledgeAnswer(
            messages=[],
            sources=[],
            personalization=ContextMetadata(),
            model_override=None,
        )

    async def empty_stream(*_args, **_kwargs):
        yield OllamaStreamEvent(done=True, metadata={})

    async def save_assistant(*args):
        persisted_assistants.append(args[-1])

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", fake_prepare)
    monkeypatch.setattr(knowledge_route.ollama_service, "stream_chat", empty_stream)
    monkeypatch.setattr(
        knowledge_route.conversation_service,
        "append_assistant_message_for_request",
        save_assistant,
    )
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask/stream",
            json={"question": "Visible question"},
        )
    finally:
        app.dependency_overrides.clear()

    assert persisted_assistants == []
    assert "event: error" in response.text
    assert "model_inference_empty_response" in response.text
