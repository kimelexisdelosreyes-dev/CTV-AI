import uuid

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import developer
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app
from app.services.model_router import configured_default_model
from app.services.performance_event_store import performance_event_store


def make_admin() -> User:
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        password_hash="not-used",
        role=UserRole.admin,
    )


async def current_user():
    return make_admin()


async def fake_db():
    yield object()


def enable_developer_overrides() -> None:
    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = fake_db
    performance_event_store.set_enabled(True)


def clear_developer_overrides() -> None:
    app.dependency_overrides.clear()
    performance_event_store.clear()
    performance_event_store.set_enabled(False)


def test_models_endpoint_lists_available_models(monkeypatch) -> None:
    default_model = configured_default_model()
    comparison_model = "comparison:test"

    async def list_models():
        return {default_model, comparison_model}

    monkeypatch.setattr(developer.ollama_service, "list_models", list_models)
    enable_developer_overrides()

    try:
        response = TestClient(app).get("/api/v1/developer/models")
    finally:
        clear_developer_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "default_model": default_model,
        "available_models": sorted([default_model, comparison_model]),
    }


def test_benchmark_rejects_default_model(monkeypatch) -> None:
    default_model = configured_default_model()

    async def list_models():
        return {default_model, "comparison:test"}

    monkeypatch.setattr(developer.ollama_service, "list_models", list_models)
    enable_developer_overrides()

    try:
        response = TestClient(app).post(
            "/api/v1/developer/models/benchmark",
            json={"comparison_model": default_model},
        )
    finally:
        clear_developer_overrides()

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Choose a comparison model that is not the current default model."
    )


def test_benchmark_rejects_unavailable_model(monkeypatch) -> None:
    async def list_models():
        return {"qwen3:14b", "qwen3:4b"}

    monkeypatch.setattr(developer.ollama_service, "list_models", list_models)
    enable_developer_overrides()

    try:
        response = TestClient(app).post(
            "/api/v1/developer/models/benchmark",
            json={"comparison_model": "not-installed"},
        )
    finally:
        clear_developer_overrides()

    assert response.status_code == 400
    assert response.json()["detail"] == "Comparison model is not installed or available."


def test_benchmark_returns_409_when_lock_is_held(monkeypatch) -> None:
    async def list_models():
        return {"qwen3:14b", "qwen3:4b"}

    monkeypatch.setattr(developer.ollama_service, "list_models", list_models)
    monkeypatch.setattr(developer.benchmark_lock, "locked", lambda: True)
    enable_developer_overrides()

    try:
        response = TestClient(app).post(
            "/api/v1/developer/models/benchmark",
            json={"comparison_model": "qwen3:4b"},
        )
    finally:
        clear_developer_overrides()

    assert response.status_code == 409
    assert response.json()["detail"] == "A model benchmark is already running."


def test_benchmark_uses_request_scoped_model_override(monkeypatch) -> None:
    warmups: list[str] = []
    calls: list[str | None] = []

    async def warmup(model_name: str) -> None:
        warmups.append(model_name)

    async def fake_answer_with_knowledge(**kwargs):
        instrumentation = kwargs["instrumentation"]
        calls.append(kwargs["model_override"])
        instrumentation.record_route("general", 0.45, [])
        instrumentation.record_prompt([{"role": "user", "content": "safe count"}])
        instrumentation.add_duration("ollama_request_ms", 0.5)
        instrumentation.record_answer("safe answer")
        return "safe answer", [], None

    monkeypatch.setattr(developer, "answer_with_knowledge", fake_answer_with_knowledge)

    results = developer.asyncio.run(
        developer.run_model_benchmark(
            default_model="qwen3:14b",
            comparison_model="qwen3:4b",
            current_user=make_admin(),
            db=object(),
            warmup=warmup,
        )
    )

    assert warmups == ["qwen3:14b", "qwen3:4b"]
    assert calls == ["qwen3:14b"] * 3 + ["qwen3:4b"] * 3
    assert {item.model_name for item in results} == {"qwen3:14b", "qwen3:4b"}
    assert all(item.outcome == "success" for item in results)


def test_benchmark_marks_no_evidence_as_skipped(monkeypatch) -> None:
    async def warmup(_: str) -> None:
        return None

    async def fake_answer_with_knowledge(**kwargs):
        instrumentation = kwargs["instrumentation"]
        instrumentation.record_route("policy", 0.76, ["company-policies"])
        instrumentation.record_answer(
            "I could not find relevant approved company knowledge for this request."
        )
        return "fallback", [], None

    monkeypatch.setattr(developer, "answer_with_knowledge", fake_answer_with_knowledge)

    results = developer.asyncio.run(
        developer.run_model_benchmark(
            default_model="qwen3:14b",
            comparison_model="qwen3:4b",
            current_user=make_admin(),
            db=object(),
            warmup=warmup,
        )
    )

    assert all(item.outcome == "skipped_no_evidence" for item in results)
    assert all(item.skipped_no_evidence for item in results)
    assert all(item.ollama_request_ms == 0 for item in results)


def test_benchmark_response_excludes_prompt_and_answer_text(monkeypatch) -> None:
    async def list_models():
        return {"qwen3:14b", "qwen3:4b"}

    async def run_model_benchmark(**_):
        return [
            developer.ModelBenchmarkResultPublic(
                model_name="qwen3:14b",
                case_label="leave_policy",
                outcome="success",
                total_request_ms=100,
                ollama_request_ms=80,
                estimated_input_tokens=25,
                estimated_output_tokens=10,
                tokens_per_second=12.5,
                answer_character_count=40,
                routed_intent="policy",
                skipped_no_evidence=False,
                error_category=None,
            )
        ]

    monkeypatch.setattr(developer.ollama_service, "list_models", list_models)
    monkeypatch.setattr(developer, "run_model_benchmark", run_model_benchmark)
    enable_developer_overrides()

    try:
        response = TestClient(app).post(
            "/api/v1/developer/models/benchmark",
            json={"comparison_model": "qwen3:4b"},
        )
    finally:
        clear_developer_overrides()

    serialized = str(response.json())

    assert response.status_code == 200
    assert "What is our leave policy?" not in serialized
    assert "safe answer" not in serialized
    assert "results" in response.json()
