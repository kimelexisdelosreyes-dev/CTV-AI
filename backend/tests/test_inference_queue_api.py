import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import knowledge as knowledge_route
from app.api.routes import runtime as runtime_route
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app
from app.schemas.context import ContextMetadata
from app.services.inference_queue import (
    InferenceQueueError,
    QueueAdmissionResult,
)
from app.services.knowledge_service import PreparedKnowledgeAnswer
from app.services.ollama_service import OllamaStreamEvent


def user(role: UserRole = UserRole.employee) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        full_name="Queue User",
        password_hash="not-used",
        role=role,
    )


async def fake_db():
    yield object()


def admission_result(**overrides) -> QueueAdmissionResult:
    values = {
        "admitted": False,
        "queued": True,
        "rejected": False,
        "queue_position": 2,
        "estimated_wait_seconds": 3.0,
        "rejection_reason": None,
        "priority": "interactive_fast",
        "model_name": "qwen3:8b",
        "wait_duration_ms": 0.0,
        "queue_depth_at_entry": 1,
    }
    values.update(overrides)
    return QueueAdmissionResult(**values)


def test_diagnostics_require_admin_and_return_aggregates(monkeypatch) -> None:
    async def employee():
        return user()

    async def admin():
        return user(UserRole.admin)

    async def safe_status():
        return {"active_global": 1, "queued_total": 2}

    monkeypatch.setattr(runtime_route.inference_queue, "status", safe_status)
    app.dependency_overrides[get_current_user] = employee
    try:
        forbidden = TestClient(app).get("/api/v1/runtime/inference/status")
        app.dependency_overrides[get_current_user] = admin
        allowed = TestClient(app).get("/api/v1/runtime/inference/status")
    finally:
        app.dependency_overrides.clear()

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json() == {"active_global": 1, "queued_total": 2}


def test_non_streaming_overload_is_safe_and_has_retry_after(monkeypatch) -> None:
    async def current_user():
        return user()

    async def overloaded(**_):
        result = admission_result(
            queued=False,
            rejected=True,
            rejection_reason="queue_full",
        )
        raise InferenceQueueError(
            "queue_full",
            status_code=429,
            retry_after_seconds=2,
            result=result,
        )

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", overloaded)
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask",
            json={"question": "private overload question"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "2"
    assert response.headers["X-Error-Category"] == "queue_full"
    assert response.json() == {
        "detail": "Inference capacity is temporarily unavailable. Please retry shortly."
    }
    assert "private overload question" not in response.text


def test_stream_emits_queue_status_without_fake_tokens(monkeypatch) -> None:
    async def current_user():
        return user()

    async def prepared(**_):
        return PreparedKnowledgeAnswer(
            messages=[{"role": "user", "content": "hidden prompt"}],
            sources=[],
            personalization=ContextMetadata(),
            model_override="qwen3:8b",
        )

    async def stream(*_args, **_kwargs):
        yield OllamaStreamEvent(text="Real token")
        yield OllamaStreamEvent(done=True, metadata={})

    final_result = admission_result(
        admitted=True,
        queued=True,
        wait_duration_ms=5.0,
    )

    class Lease:
        result = final_result
        model_name = "qwen3:8b"
        active_global = 1
        active_for_model = 1
        user_active_count = 1

        async def release(self, **_):
            return 6.0

    class Admission:
        initial_result = admission_result()

        async def wait(self, **_):
            return Lease()

    class Queue:
        config = SimpleNamespace(default_timeout_seconds=1.0)

        async def submit(self, **_):
            return Admission()

        def record_result(self, instrumentation, result):
            instrumentation.record_metric(
                "inference_queue_priority", result.priority
            )

        def record_lease(self, instrumentation, lease):
            self.record_result(instrumentation, lease.result)

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(knowledge_route, "answer_with_knowledge", prepared)
    monkeypatch.setattr(knowledge_route, "inference_queue", Queue())
    monkeypatch.setattr(knowledge_route.ollama_service, "stream_chat", stream)
    try:
        response = TestClient(app).post(
            "/api/v1/knowledge/ask/stream",
            json={"question": "private streaming question"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text.count("event: queue_status") == 1
    assert response.text.count("event: token") == 1
    assert "Real token" in response.text
    assert "hidden prompt" not in response.text
    assert "private streaming question" not in response.text
