import uuid

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.models.user import User, UserRole
from app.main import app
from app.services.performance_event_store import (
    PerformanceEventStore,
    performance_event_store,
    sanitize_event,
)


def make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        full_name="Test User",
        password_hash="not-used",
        role=role,
    )


def make_event(index: int, **overrides):
    event = {
        "timestamp": f"2026-07-16T00:00:{index:02d}+00:00",
        "outcome": "success",
        "routed_intent": "general",
        "routing_confidence": 0.45,
        "total_endpoint_ms": float(index),
        "intelligence_router_ms": 1.0,
        "employee_context_ms": 2.0,
        "monday_operational_context_ms": 3.0,
        "embedding_ms": 4.0,
        "qdrant_vector_search_ms": 5.0,
        "prompt_assembly_ms": 6.0,
        "ollama_request_ms": 7.0,
        "prompt_character_count": 100,
        "prompt_size": 100,
        "estimated_input_token_count": 25,
        "estimated_output_token_count": 10,
        "tokens_per_second": 20.0,
        "answer_character_count": 40,
        "collection_count": 1,
        "retrieved_chunk_count": 2,
        "operational_task_count": 0,
        "routed_collection_searches": [
            {
                "collection": "general",
                "duration_ms": 9.0,
                "retrieved_chunk_count": 2,
            }
        ],
        "model_name": "qwen3:14b",
        "gpu_utilization": None,
        "cpu_utilization": None,
    }
    event.update(overrides)
    return event


def test_event_store_keeps_latest_50_events() -> None:
    store = PerformanceEventStore()
    store.set_enabled(True)

    for index in range(60):
        store.record(make_event(index))

    recent = store.recent()

    assert len(recent) == 50
    assert recent[0]["total_endpoint_ms"] == 59.0
    assert recent[-1]["total_endpoint_ms"] == 10.0


def test_summary_averages_median_and_p95_are_correct() -> None:
    store = PerformanceEventStore()
    store.set_enabled(True)

    for index in range(1, 101):
        store.record(
            make_event(
                index,
                outcome="error" if index == 100 else "success",
                routed_intent="operations" if index % 2 == 0 else "general",
                ollama_request_ms=10.0,
                monday_operational_context_ms=20.0,
                employee_context_ms=30.0,
                embedding_ms=40.0,
                qdrant_vector_search_ms=50.0,
                estimated_input_token_count=100,
                tokens_per_second=5.0,
            )
        )

    summary = store.summary()

    assert summary["request_count"] == 50
    assert summary["success_count"] == 49
    assert summary["failure_count"] == 1
    assert summary["average_total_duration_ms"] == 75.5
    assert summary["median_total_duration_ms"] == 75.5
    assert summary["p95_total_duration_ms"] == 97.0
    assert summary["average_ollama_duration_ms"] == 10.0
    assert summary["average_monday_duration_ms"] == 20.0
    assert summary["average_employee_context_duration_ms"] == 30.0
    assert summary["average_embedding_duration_ms"] == 40.0
    assert summary["average_qdrant_duration_ms"] == 50.0
    assert summary["average_estimated_input_tokens"] == 100.0
    assert summary["average_tokens_per_second"] == 5.0
    assert summary["slowest_stage"] == "qdrant_vector_search"
    assert summary["counts_by_routed_intent"] == {"general": 25, "operations": 25}


def test_sensitive_fields_are_not_serialized() -> None:
    event = sanitize_event(
        make_event(
            1,
            question="secret question",
            answer="secret answer",
            prompt="secret prompt",
            Authorization="Bearer secret",
            employee_id="secret-user",
            filename="secret.pdf",
            api_token="secret-token",
        )
    )

    serialized = str(event)

    assert "secret" not in serialized
    assert "Authorization" not in serialized
    assert "filename" not in serialized


def test_non_admin_users_are_denied() -> None:
    async def current_user():
        return make_user(UserRole.employee)

    app.dependency_overrides[get_current_user] = current_user
    performance_event_store.set_enabled(True)

    try:
        response = TestClient(app).get("/api/v1/developer/performance/recent")
    finally:
        app.dependency_overrides.clear()
        performance_event_store.clear()
        performance_event_store.set_enabled(False)

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."


def test_developer_mode_disabled_returns_403() -> None:
    async def current_user():
        return make_user(UserRole.admin)

    app.dependency_overrides[get_current_user] = current_user
    performance_event_store.clear()
    performance_event_store.set_enabled(False)

    try:
        response = TestClient(app).get("/api/v1/developer/performance/recent")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Developer mode is disabled."


def test_clear_endpoint_removes_stored_metrics() -> None:
    async def current_user():
        return make_user(UserRole.admin)

    app.dependency_overrides[get_current_user] = current_user
    performance_event_store.clear()
    performance_event_store.set_enabled(True)
    performance_event_store.record(make_event(1))

    try:
        response = TestClient(app).delete("/api/v1/developer/performance/recent")
        recent = TestClient(app).get("/api/v1/developer/performance/recent")
    finally:
        app.dependency_overrides.clear()
        performance_event_store.clear()
        performance_event_store.set_enabled(False)

    assert response.status_code == 204
    assert recent.status_code == 200
    assert recent.json() == []


def test_status_endpoint_toggles_developer_mode() -> None:
    async def current_user():
        return make_user(UserRole.admin)

    app.dependency_overrides[get_current_user] = current_user
    performance_event_store.clear()
    performance_event_store.set_enabled(False)

    try:
        enabled = TestClient(app).put(
            "/api/v1/developer/status",
            json={"enabled": True},
        )
        status = TestClient(app).get("/api/v1/developer/status")
    finally:
        app.dependency_overrides.clear()
        performance_event_store.clear()
        performance_event_store.set_enabled(False)

    assert enabled.status_code == 200
    assert enabled.json() == {"enabled": True}
    assert status.json() == {"enabled": True}
