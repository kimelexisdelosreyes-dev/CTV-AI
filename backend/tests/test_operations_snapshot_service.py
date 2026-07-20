import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.connectors.base import ConnectorError
from app.connectors.models import ConnectorProject, ConnectorTask
from app.core.config import settings
from app.services import operations_snapshot_service as snapshot_module
from app.services.operations_snapshot_service import (
    OperationsSnapshotService,
    OperationsSyncEmptyResultError,
    OperationsSyncInProgressError,
)
from app.services.service_errors import CompanyBrainServiceError


@pytest.fixture(autouse=True)
def avoid_live_database_lock(monkeypatch):
    @asynccontextmanager
    async def acquired(_service):
        yield True, 0.0

    monkeypatch.setattr(
        OperationsSnapshotService,
        "_database_refresh_lock",
        acquired,
    )


def task(external_id: str, title: str) -> ConnectorTask:
    return ConnectorTask(
        external_id=external_id,
        title=title,
        metadata={"board_name": "Production", "group_title": "This week"},
    )


@pytest.mark.anyio
async def test_sync_deduplicates_mocked_monday_tasks(monkeypatch) -> None:
    service = OperationsSnapshotService()
    snapshot_id = uuid.uuid4()
    captured: dict[str, object] = {}

    async def create(*_):
        return snapshot_id

    async def no_stale():
        return False

    async def no_running():
        return False

    async def tasks(_name):
        return [task("1", "Older"), task("1", "Latest"), task("2", "Second")]

    async def projects(_name):
        return [ConnectorProject(external_id="board-1", name="Production")]

    async def complete(_id, task_items, project_items, trigger, _started):
        captured.update(tasks=task_items, projects=project_items, trigger=trigger)
        return service.response(None)

    monkeypatch.setattr(service, "_create_running_snapshot", create)
    monkeypatch.setattr(service, "recover_stale_running", no_stale)
    monkeypatch.setattr(service, "has_persisted_running", no_running)
    monkeypatch.setattr(service, "_complete_snapshot", complete)
    monkeypatch.setattr(snapshot_module.connector_manager, "tasks", tasks)
    monkeypatch.setattr(snapshot_module.connector_manager, "projects", projects)

    await service.sync("manual")

    assert [item.external_id for item in captured["tasks"]] == ["1", "2"]
    assert captured["tasks"][0].title == "Latest"
    assert captured["trigger"] == "manual"
    assert service.sync_running is False


@pytest.mark.anyio
async def test_failed_sync_marks_only_new_snapshot_and_keeps_safe_error(monkeypatch) -> None:
    service = OperationsSnapshotService()
    snapshot_id = uuid.uuid4()
    failure: dict[str, str] = {}

    async def create(*_):
        return snapshot_id

    async def no_stale():
        return False

    async def no_running():
        return False

    async def failed_tasks(_name):
        raise ConnectorError("private upstream detail")

    async def projects(_name):
        return []

    async def fail(_id, _trigger, category, safe_error, _metrics=None):
        failure.update(category=category, safe_error=safe_error)

    monkeypatch.setattr(service, "_create_running_snapshot", create)
    monkeypatch.setattr(service, "recover_stale_running", no_stale)
    monkeypatch.setattr(service, "has_persisted_running", no_running)
    monkeypatch.setattr(service, "_fail_snapshot", fail)
    monkeypatch.setattr(snapshot_module.connector_manager, "tasks", failed_tasks)
    monkeypatch.setattr(snapshot_module.connector_manager, "projects", projects)

    with pytest.raises(CompanyBrainServiceError):
        await service.sync("background")

    assert failure["category"] == "operations_sync_failed"
    assert "private upstream detail" not in failure["safe_error"]
    assert service.sync_running is False


@pytest.mark.anyio
async def test_sync_timeout_is_safe(monkeypatch) -> None:
    service = OperationsSnapshotService()
    failure: dict[str, str] = {}

    async def create(*_):
        return uuid.uuid4()

    async def no_stale():
        return False

    async def no_running():
        return False

    async def slow(_name):
        await asyncio.sleep(1)
        return []

    async def fail(_id, _trigger, category, safe_error, _metrics=None):
        failure.update(category=category, safe_error=safe_error)

    monkeypatch.setattr(settings, "operations_sync_timeout_seconds", 0.001)
    monkeypatch.setattr(service, "_create_running_snapshot", create)
    monkeypatch.setattr(service, "recover_stale_running", no_stale)
    monkeypatch.setattr(service, "has_persisted_running", no_running)
    monkeypatch.setattr(service, "_fail_snapshot", fail)
    monkeypatch.setattr(snapshot_module.connector_manager, "tasks", slow)
    monkeypatch.setattr(snapshot_module.connector_manager, "projects", slow)

    with pytest.raises(CompanyBrainServiceError) as exc:
        await service.sync("manual")

    assert exc.value.category == "operations_sync_timeout"
    assert failure["category"] == "operations_sync_timeout"
    assert service.sync_running is False


@pytest.mark.anyio
async def test_overlapping_sync_is_rejected_before_fetch() -> None:
    service = OperationsSnapshotService()
    await service._sync_lock.acquire()
    try:
        with pytest.raises(OperationsSyncInProgressError):
            await service.sync("manual")
    finally:
        service._sync_lock.release()


def test_snapshot_freshness_and_empty_state(monkeypatch) -> None:
    service = OperationsSnapshotService()
    monkeypatch.setattr(settings, "ctv_one_operations_snapshot_fresh_seconds", 300)
    monkeypatch.setattr(settings, "ctv_one_operations_snapshot_aging_seconds", 500)
    snapshot = SimpleNamespace(
        id=uuid.uuid4(),
        status="success",
        fetched_at=datetime.now(timezone.utc) - timedelta(seconds=600),
        task_count=0,
        tasks=[],
        metadata_json={},
        safe_error=None,
    )

    response = service.response(snapshot)

    assert response.freshness == "stale"
    assert response.age_seconds >= 600
    assert service.response(None).freshness == "unavailable"


@pytest.mark.anyio
async def test_cancelled_sync_records_failure_and_releases_lock(monkeypatch) -> None:
    service = OperationsSnapshotService()
    failure: dict[str, str] = {}
    started = asyncio.Event()

    async def create(*_):
        started.set()
        return uuid.uuid4()

    async def slow(_name):
        await asyncio.sleep(10)
        return []

    async def fail(_id, _trigger, category, safe_error, _metrics=None):
        failure.update(category=category, safe_error=safe_error)

    monkeypatch.setattr(service, "_create_running_snapshot", create)
    monkeypatch.setattr(service, "_fail_snapshot", fail)
    monkeypatch.setattr(service, "recover_stale_running", lambda: asyncio.sleep(0, result=False))
    monkeypatch.setattr(service, "has_persisted_running", lambda: asyncio.sleep(0, result=False))
    monkeypatch.setattr(snapshot_module.connector_manager, "tasks", slow)
    monkeypatch.setattr(snapshot_module.connector_manager, "projects", slow)

    job = asyncio.create_task(service.sync("background"))
    await started.wait()
    job.cancel()
    with pytest.raises(asyncio.CancelledError):
        await job

    assert failure["category"] == "operations_sync_cancelled"
    assert service.sync_running is False


@pytest.mark.anyio
async def test_stale_running_snapshot_is_recovered(monkeypatch) -> None:
    service = OperationsSnapshotService()
    running = SimpleNamespace(
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        failed_at=None,
        error_category=None,
        safe_error=None,
    )
    committed = False

    class Result:
        def scalars(self):
            return self

        def all(self):
            return [running]

    class Session:
        async def execute(self, _statement):
            return Result()

        async def commit(self):
            nonlocal committed
            committed = True

    class SessionContext:
        async def __aenter__(self):
            return Session()

        async def __aexit__(self, *_):
            return None

    monkeypatch.setattr(snapshot_module, "AsyncSessionLocal", SessionContext)

    recovered = await service.recover_stale_running()

    assert recovered is True
    assert committed is True
    assert running.status == "failed"
    assert running.error_category == "operations_sync_stale_recovered"


@pytest.mark.anyio
async def test_sync_rejects_suspicious_empty_and_preserves_previous_snapshot(
    monkeypatch,
) -> None:
    service = OperationsSnapshotService()
    snapshot_id = uuid.uuid4()
    previous = snapshot_module.OperationsSnapshotResponse(
        snapshot_id=uuid.uuid4(),
        status="success",
        freshness="fresh",
        fetched_at=datetime.now(timezone.utc),
        age_seconds=1,
        task_count=1,
        tasks=[task("existing", "Keep me")],
    )
    failure: dict[str, object] = {}
    completed = False

    async def fail(_id, _trigger, category, safe_error, metrics=None):
        failure.update(category=category, safe_error=safe_error, metrics=metrics)

    async def complete(*_):
        nonlocal completed
        completed = True
        return service.response(None)

    monkeypatch.setattr(
        service, "recover_stale_running", lambda: asyncio.sleep(0, result=False)
    )
    monkeypatch.setattr(
        service, "has_persisted_running", lambda: asyncio.sleep(0, result=False)
    )
    monkeypatch.setattr(
        service,
        "_create_running_snapshot",
        lambda *_: asyncio.sleep(0, result=snapshot_id),
    )
    monkeypatch.setattr(
        service, "get_snapshot_response", lambda: asyncio.sleep(0, result=previous)
    )
    monkeypatch.setattr(service, "_complete_snapshot", complete)
    monkeypatch.setattr(service, "_fail_snapshot", fail)
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "tasks",
        lambda _name: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "projects",
        lambda _name: asyncio.sleep(
            0,
            result=[ConnectorProject(external_id="board-1", name="Production")],
        ),
    )
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "task_fetch_diagnostics",
        lambda _name: {
            "boards_requested": 1,
            "groups_returned": 0,
            "raw_items_count": 0,
            "skipped_items_count": 0,
            "skip_reason_counts": {},
        },
    )

    with pytest.raises(OperationsSyncEmptyResultError) as exc:
        await service.sync("manual")

    assert exc.value.snapshot == previous
    assert completed is False
    assert failure["category"] == "operations_sync_empty_result"
    assert failure["metrics"]["empty_snapshot_rejected"] is True
    assert failure["metrics"]["previous_successful_snapshot_task_count"] == 1
    assert service.sync_running is False


@pytest.mark.anyio
async def test_sync_allows_empty_initial_snapshot(monkeypatch) -> None:
    service = OperationsSnapshotService()
    empty = service.response(None)
    completed = False

    async def complete(*_):
        nonlocal completed
        completed = True
        return empty

    monkeypatch.setattr(
        service, "recover_stale_running", lambda: asyncio.sleep(0, result=False)
    )
    monkeypatch.setattr(
        service, "has_persisted_running", lambda: asyncio.sleep(0, result=False)
    )
    monkeypatch.setattr(
        service,
        "_create_running_snapshot",
        lambda *_: asyncio.sleep(0, result=uuid.uuid4()),
    )
    monkeypatch.setattr(
        service, "get_snapshot_response", lambda: asyncio.sleep(0, result=empty)
    )
    monkeypatch.setattr(service, "_complete_snapshot", complete)
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "tasks",
        lambda _name: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "projects",
        lambda _name: asyncio.sleep(
            0,
            result=[ConnectorProject(external_id="board-1", name="Production")],
        ),
    )
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "task_fetch_diagnostics",
        lambda _name: {},
    )

    result = await service.sync("manual")

    assert completed is True
    assert result.task_count == 0


@pytest.mark.anyio
async def test_task_insert_failure_marks_attempt_failed(monkeypatch) -> None:
    service = OperationsSnapshotService()
    snapshot_id = uuid.uuid4()
    failure: dict[str, object] = {}

    async def fail(_id, _trigger, category, safe_error, metrics=None):
        failure.update(category=category, safe_error=safe_error, metrics=metrics)

    async def insert_failure(*_):
        raise RuntimeError("simulated insert failure")

    monkeypatch.setattr(
        service, "recover_stale_running", lambda: asyncio.sleep(0, result=False)
    )
    monkeypatch.setattr(
        service, "has_persisted_running", lambda: asyncio.sleep(0, result=False)
    )
    monkeypatch.setattr(
        service,
        "_create_running_snapshot",
        lambda *_: asyncio.sleep(0, result=snapshot_id),
    )
    monkeypatch.setattr(service, "_complete_snapshot", insert_failure)
    monkeypatch.setattr(service, "_fail_snapshot", fail)
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "tasks",
        lambda _name: asyncio.sleep(0, result=[task("1", "Task")]),
    )
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "projects",
        lambda _name: asyncio.sleep(
            0,
            result=[ConnectorProject(external_id="board-1", name="Production")],
        ),
    )
    monkeypatch.setattr(
        snapshot_module.connector_manager,
        "task_fetch_diagnostics",
        lambda _name: {"raw_items_count": 1},
    )

    with pytest.raises(CompanyBrainServiceError) as exc:
        await service.sync("manual")

    assert exc.value.category == "operations_sync_failed"
    assert failure["category"] == "operations_sync_failed"
    assert failure["metrics"]["normalized_tasks_count"] == 1
    assert "simulated insert failure" not in str(failure["safe_error"])
    assert service.sync_running is False
