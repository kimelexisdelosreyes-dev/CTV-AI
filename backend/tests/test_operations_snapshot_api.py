import uuid

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import operations as operations_route
from app.connectors.models import ConnectorTask
from app.db.models.user import User, UserRole
from app.main import app
from app.schemas.operations import OperationsSnapshotResponse, OperationsSyncStatusResponse
from app.services.operations_snapshot_service import (
    OperationsSyncEmptyResultError,
    OperationsSyncInProgressError,
)


def user() -> User:
    return User(
        id=uuid.uuid4(),
        email="operations@example.com",
        full_name="Operations User",
        password_hash="not-used",
        role=UserRole.employee,
    )


async def current_user():
    return user()


def empty_snapshot() -> OperationsSnapshotResponse:
    return OperationsSnapshotResponse(
        snapshot_id=None,
        status="empty",
        freshness="empty",
        fetched_at=None,
        age_seconds=None,
        task_count=0,
    )


def test_operations_endpoints_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/operations/snapshot").status_code == 401
    assert client.post("/api/v1/operations/refresh").status_code == 401
    assert client.get("/api/v1/operations/sync/status").status_code == 401


def test_snapshot_refresh_and_status_return_safe_shapes(monkeypatch) -> None:
    async def snapshot():
        return empty_snapshot()

    async def refresh(trigger):
        assert trigger == "manual"
        return empty_snapshot()

    async def status():
        return OperationsSyncStatusResponse(
            state="idle",
            running=False,
            status="idle",
            started_at=None,
            last_success_at=None,
            last_failure_at=None,
            latest_snapshot_id=None,
            latest_snapshot_age_seconds=None,
            latest_snapshot_status="empty",
            safe_error=None,
            can_refresh=True,
        )

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(operations_route.operations_snapshot_service, "get_snapshot_response", snapshot)
    monkeypatch.setattr(operations_route.operations_snapshot_service, "sync", refresh)
    monkeypatch.setattr(operations_route.operations_snapshot_service, "status", status)
    client = TestClient(app)
    try:
        snapshot_response = client.get("/api/v1/operations/snapshot")
        refresh_response = client.post("/api/v1/operations/refresh")
        status_response = client.get("/api/v1/operations/sync/status")
    finally:
        app.dependency_overrides.clear()

    assert snapshot_response.status_code == 200
    assert refresh_response.status_code == 200
    assert status_response.status_code == 200
    combined = str(
        [snapshot_response.json(), refresh_response.json(), status_response.json()]
    ).lower()
    assert "token" not in combined
    assert "credential" not in combined


def test_refresh_reports_overlapping_sync_as_running(monkeypatch) -> None:
    async def overlapping(_trigger):
        raise OperationsSyncInProgressError()

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(operations_route.operations_snapshot_service, "sync", overlapping)
    async def snapshot():
        return empty_snapshot()

    monkeypatch.setattr(
        operations_route.operations_snapshot_service,
        "get_snapshot_response",
        snapshot,
    )
    try:
        response = TestClient(app).post("/api/v1/operations/refresh")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert response.json()["running"] is True
    assert response.json()["message"] == "Refresh already in progress."


def test_refresh_preserves_snapshot_when_empty_result_is_rejected(monkeypatch) -> None:
    previous = OperationsSnapshotResponse(
        snapshot_id=uuid.uuid4(),
        status="success",
        freshness="fresh",
        fetched_at=None,
        age_seconds=1,
        task_count=1,
        tasks=[ConnectorTask(external_id="task-1", title="Keep me")],
    )

    async def suspicious_empty(_trigger):
        raise OperationsSyncEmptyResultError(previous)

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(
        operations_route.operations_snapshot_service, "sync", suspicious_empty
    )
    try:
        response = TestClient(app).post("/api/v1/operations/refresh")
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "suspicious_empty"
    assert payload["running"] is False
    assert payload["snapshot"]["task_count"] == 1
    assert payload["snapshot"]["tasks"][0]["title"] == "Keep me"
