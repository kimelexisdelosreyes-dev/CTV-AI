import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.connectors.monday import MondayApiError
from app.connectors.models import ConnectorProject, ConnectorTask
from app.core.config import settings
from app.services import operations_snapshot_service as snapshot_module
from app.services.operations_snapshot_service import (
    OperationsSnapshotService,
    operations_content_hash,
    operations_sync_loop,
)


def task(
    external_id: str,
    *,
    status: str = "Working",
    priority: str = "High",
    updated_at: str = "2026-01-01T00:00:00Z",
) -> ConnectorTask:
    return ConnectorTask(
        external_id=external_id,
        title=f"Task {external_id}",
        status=status,
        priority=priority,
        due_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        assignee_ids=["2", "1"],
        project_id="board-1",
        metadata={"board_name": "Production", "updated_at": updated_at},
    )


def project() -> ConnectorProject:
    return ConnectorProject(external_id="board-1", name="Production")


def test_content_hash_is_stable_and_excludes_volatile_update_timestamp() -> None:
    first = operations_content_hash(
        [task("2"), task("1", updated_at="2026-01-01T00:00:00Z")],
        [project()],
    )
    reordered = operations_content_hash(
        [task("1", updated_at="2026-07-01T00:00:00Z"), task("2")],
        [project()],
    )
    changed = operations_content_hash(
        [task("1", status="Done"), task("2")],
        [project()],
    )
    assert first == reordered
    assert changed != first


@pytest.mark.anyio
async def test_retry_transient_timeout_and_rate_limit(monkeypatch) -> None:
    service = OperationsSnapshotService()
    calls = 0

    async def tasks(_name):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise MondayApiError(
                "Monday rate limit reached.",
                category="monday_rate_limited",
                retryable=True,
            )
        return [task("1")]

    async def projects(_name):
        return [project()]

    monkeypatch.setattr(settings, "ctv_one_monday_snapshot_retry_attempts", 3)
    monkeypatch.setattr(settings, "ctv_one_monday_snapshot_retry_base_seconds", 0)
    monkeypatch.setattr(snapshot_module.connector_manager, "tasks", tasks)
    monkeypatch.setattr(snapshot_module.connector_manager, "projects", projects)

    tasks_result, _, attempts = await service._fetch_with_retries()
    assert attempts == 2
    assert tasks_result[0].external_id == "1"


@pytest.mark.anyio
async def test_retry_on_timeout(monkeypatch) -> None:
    service = OperationsSnapshotService()
    calls = 0

    async def tasks(_name):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError()
        return [task("1")]

    monkeypatch.setattr(settings, "ctv_one_monday_snapshot_retry_attempts", 3)
    monkeypatch.setattr(settings, "ctv_one_monday_snapshot_retry_base_seconds", 0)
    monkeypatch.setattr(snapshot_module.connector_manager, "tasks", tasks)
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "projects",
        lambda _name: asyncio.sleep(0, result=[project()]),
    )
    _, _, attempts = await service._fetch_with_retries()
    assert attempts == 2


@pytest.mark.anyio
async def test_authentication_failure_is_not_retried(monkeypatch) -> None:
    service = OperationsSnapshotService()
    calls = 0

    async def unauthorized(_name):
        nonlocal calls
        calls += 1
        raise MondayApiError(
            "Monday authentication failed.",
            category="monday_authentication_failed",
        )

    monkeypatch.setattr(snapshot_module.connector_manager, "tasks", unauthorized)
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "projects",
        lambda _name: asyncio.sleep(0, result=[]),
    )
    with pytest.raises(MondayApiError):
        await service._fetch_with_retries()
    assert calls == 1


@pytest.mark.anyio
async def test_advisory_lock_is_released_after_exception(monkeypatch) -> None:
    service = OperationsSnapshotService()
    statements: list[str] = []

    class Connection:
        async def scalar(self, statement, _params):
            statements.append(str(statement))
            return True

        async def execute(self, statement, _params):
            statements.append(str(statement))

        async def close(self):
            statements.append("closed")

    class Engine:
        async def connect(self):
            return Connection()

    monkeypatch.setattr(snapshot_module, "engine", Engine())
    with pytest.raises(RuntimeError):
        async with service._database_refresh_lock() as (acquired, _):
            assert acquired is True
            raise RuntimeError("simulated")
    assert any("pg_advisory_unlock" in statement for statement in statements)
    assert statements[-1] == "closed"


@pytest.mark.anyio
@pytest.mark.parametrize("same_content", [False, True])
async def test_atomic_activation_and_content_aware_cache_invalidation(
    monkeypatch, same_content
) -> None:
    service = OperationsSnapshotService()
    snapshot_id = uuid.uuid4()
    previous = SimpleNamespace(
        id=uuid.uuid4(),
        status="active",
        content_hash=(
            operations_content_hash([task("1")], [project()])
            if same_content
            else "old-hash"
        ),
    )
    candidate = SimpleNamespace(
        id=snapshot_id,
        status="pending",
        tasks=[],
        metadata_json={},
        safe_error=None,
    )
    commits = 0

    class CountResult:
        def scalar_one(self):
            return 1

    class Session:
        async def get(self, *_args, **_kwargs):
            return candidate

        def add(self, _value):
            assert candidate.status == "pending"
            assert previous.status == "active"

        async def flush(self):
            return None

        async def execute(self, _statement):
            return CountResult()

        async def commit(self):
            nonlocal commits
            commits += 1
            if commits == 1:
                assert candidate.status == "active"
                assert previous.status == "retired"

        async def refresh(self, *_args, **_kwargs):
            return None

    class SessionContext:
        async def __aenter__(self):
            return Session()

        async def __aexit__(self, *_args):
            return None

    invalidations = 0

    async def invalidate():
        nonlocal invalidations
        invalidations += 1
        return 4

    async def latest(_db, status, **_kwargs):
        return previous if status == "active" else None

    monkeypatch.setattr(snapshot_module, "AsyncSessionLocal", SessionContext)
    monkeypatch.setattr(service, "_latest", latest)
    monkeypatch.setattr(snapshot_module.semantic_cache, "invalidate_operations", invalidate)
    response = await service._complete_snapshot(
        snapshot_id,
        [task("1")],
        [project()],
        "manual",
        snapshot_module.perf_counter(),
    )
    assert response.status == "active"
    assert invalidations == (0 if same_content else 1)
    assert response.cache_invalidation_count == (0 if same_content else 4)
    assert response.content_changed is (not same_content)


@pytest.mark.anyio
async def test_partial_candidate_write_never_replaces_active(monkeypatch) -> None:
    service = OperationsSnapshotService()
    previous = SimpleNamespace(id=uuid.uuid4(), status="active", content_hash="old")
    candidate = SimpleNamespace(
        id=uuid.uuid4(), status="pending", tasks=[], metadata_json={}, safe_error=None
    )

    class Session:
        async def get(self, *_args, **_kwargs):
            return candidate

        def add(self, _value):
            raise RuntimeError("simulated partial write")

    class SessionContext:
        async def __aenter__(self):
            return Session()

        async def __aexit__(self, *_args):
            return None

    async def latest(_db, _status, **_kwargs):
        return previous

    monkeypatch.setattr(snapshot_module, "AsyncSessionLocal", SessionContext)
    monkeypatch.setattr(service, "_latest", latest)
    with pytest.raises(RuntimeError):
        await service._complete_snapshot(
            candidate.id,
            [task("1")],
            [project()],
            "manual",
            snapshot_module.perf_counter(),
        )
    assert candidate.status == "pending"
    assert previous.status == "active"


@pytest.mark.anyio
async def test_scheduler_failure_does_not_escape(monkeypatch) -> None:
    stop = asyncio.Event()

    async def fail(_trigger):
        stop.set()
        raise RuntimeError("simulated scheduler failure")

    monkeypatch.setattr(settings, "ctv_one_monday_snapshot_refresh_on_startup", True)
    monkeypatch.setattr(snapshot_module.operations_snapshot_service, "sync", fail)
    await operations_sync_loop(stop)
