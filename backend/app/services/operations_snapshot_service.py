import asyncio
import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.connectors.base import ConnectorError
from app.connectors.manager import connector_manager
from app.connectors.models import ConnectorProject, ConnectorTask
from app.core.config import settings
from app.db.models.operations_snapshot import OperationTask, OperationsSnapshot
from app.db.session import AsyncSessionLocal
from app.schemas.operations import OperationsSnapshotResponse, OperationsSyncStatusResponse
from app.services.service_errors import CompanyBrainServiceError


performance_logger = logging.getLogger("ctv_one.performance")


class OperationsSnapshotUnavailableError(CompanyBrainServiceError):
    category = "operations_snapshot_unavailable"
    safe_detail = "Operations data is not available yet. Refresh the operations snapshot."


class OperationsSyncInProgressError(CompanyBrainServiceError):
    category = "operations_sync_in_progress"
    status_code = 409
    safe_detail = "Operations refresh is already running."


class OperationsSyncEmptyResultError(CompanyBrainServiceError):
    category = "operations_sync_empty_result"
    safe_detail = (
        "Latest refresh returned no tasks, so the previous snapshot is being shown."
    )

    def __init__(self, snapshot: OperationsSnapshotResponse) -> None:
        super().__init__()
        self.snapshot = snapshot


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class OperationsSnapshotService:
    def __init__(self) -> None:
        self._sync_lock = asyncio.Lock()

    @property
    def sync_running(self) -> bool:
        return self._sync_lock.locked()

    async def _latest(
        self,
        db: AsyncSession,
        status: str,
    ) -> OperationsSnapshot | None:
        result = await db.execute(
            select(OperationsSnapshot)
            .where(OperationsSnapshot.status == status)
            .options(selectinload(OperationsSnapshot.tasks))
            .order_by(
                OperationsSnapshot.fetched_at.desc().nullslast(),
                OperationsSnapshot.created_at.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def latest_successful(self) -> OperationsSnapshot | None:
        async with AsyncSessionLocal() as db:
            return await self._latest(db, "success")

    def freshness(self, snapshot: OperationsSnapshot | None) -> tuple[str, float | None]:
        if snapshot is None or snapshot.fetched_at is None:
            return "empty", None
        fetched_at = snapshot.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        age = max((_utcnow() - fetched_at).total_seconds(), 0.0)
        return (
            "fresh" if age <= settings.operations_snapshot_max_age_seconds else "stale",
            round(age, 3),
        )

    def task_to_connector(self, task: OperationTask) -> ConnectorTask:
        return ConnectorTask(
            external_id=task.external_id,
            title=task.title,
            status=task.status,
            priority=task.priority,
            due_at=task.due_at,
            assignee_ids=list(task.assignee_ids or []),
            project_id=task.board_id,
            url=task.url,
            metadata={
                "board_name": task.board_name,
                "group_id": task.group_id,
                "group_title": task.group_name,
                "updated_at": task.updated_at_source.isoformat()
                if task.updated_at_source
                else None,
            },
        )

    def response(self, snapshot: OperationsSnapshot | None) -> OperationsSnapshotResponse:
        freshness, age = self.freshness(snapshot)
        if snapshot is None:
            return OperationsSnapshotResponse(
                snapshot_id=None,
                status="empty",
                freshness="empty",
                fetched_at=None,
                age_seconds=None,
                task_count=0,
            )
        projects = [
            ConnectorProject.model_validate(item)
            for item in snapshot.metadata_json.get("projects", [])
        ]
        return OperationsSnapshotResponse(
            snapshot_id=snapshot.id,
            status=snapshot.status,
            freshness=freshness,
            fetched_at=snapshot.fetched_at,
            age_seconds=age,
            task_count=snapshot.task_count,
            tasks=[self.task_to_connector(task) for task in snapshot.tasks],
            projects=projects,
            safe_error=snapshot.safe_error,
        )

    async def get_snapshot_response(self) -> OperationsSnapshotResponse:
        return self.response(await self.latest_successful())

    async def recover_stale_running(self) -> bool:
        if self.sync_running:
            return False
        grace_seconds = max(settings.operations_sync_timeout_seconds * 0.25, 5.0)
        cutoff = _utcnow().timestamp() - (
            settings.operations_sync_timeout_seconds + grace_seconds
        )
        recovered = False
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(OperationsSnapshot).where(
                    OperationsSnapshot.status == "running"
                )
            )
            for snapshot in result.scalars().all():
                started_at = snapshot.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                if started_at.timestamp() >= cutoff:
                    continue
                snapshot.status = "failed"
                snapshot.failed_at = _utcnow()
                snapshot.error_category = "operations_sync_stale_recovered"
                snapshot.safe_error = (
                    "An interrupted operations refresh was recovered safely."
                )
                recovered = True
            if recovered:
                await db.commit()
        return recovered

    async def has_persisted_running(self) -> bool:
        async with AsyncSessionLocal() as db:
            return await self._latest(db, "running") is not None

    async def _create_running_snapshot(self, trigger: str, started_at: datetime) -> UUID:
        async with AsyncSessionLocal() as db:
            snapshot = OperationsSnapshot(
                source="monday",
                status="running",
                started_at=started_at,
                metadata_json={"sync_trigger": trigger},
            )
            db.add(snapshot)
            await db.commit()
            await db.refresh(snapshot)
            return snapshot.id

    async def _complete_snapshot(
        self,
        snapshot_id: UUID,
        tasks: list[ConnectorTask],
        projects: list[ConnectorProject],
        trigger: str,
        sync_started: float,
    ) -> OperationsSnapshotResponse:
        async with AsyncSessionLocal() as db:
            snapshot = await db.get(OperationsSnapshot, snapshot_id)
            if snapshot is None:
                raise OperationsSnapshotUnavailableError()
            for task in tasks:
                metadata = task.metadata or {}
                db.add(
                    OperationTask(
                        snapshot_id=snapshot.id,
                        external_id=task.external_id,
                        board_id=task.project_id,
                        board_name=metadata.get("board_name"),
                        group_id=metadata.get("group_id"),
                        group_name=metadata.get("group_title"),
                        title=task.title,
                        status=task.status,
                        priority=task.priority,
                        assignee_ids=list(task.assignee_ids),
                        owner_key=",".join(sorted(task.assignee_ids)) or None,
                        due_at=task.due_at,
                        updated_at_source=_parse_datetime(metadata.get("updated_at")),
                        url=task.url,
                    )
                )
            await db.flush()
            inserted_count = int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(OperationTask)
                        .where(OperationTask.snapshot_id == snapshot.id)
                    )
                ).scalar_one()
            )
            if inserted_count != len(tasks):
                raise CompanyBrainServiceError(
                    category="operations_snapshot_write_mismatch",
                    safe_detail="Operations snapshot could not be saved safely.",
                )
            now = _utcnow()
            snapshot.status = "success"
            snapshot.fetched_at = now
            snapshot.completed_at = now
            snapshot.task_count = len(tasks)
            snapshot.metadata_json = {
                "sync_trigger": trigger,
                "sync_duration_ms": round((perf_counter() - sync_started) * 1000, 3),
                "projects": [project.model_dump(mode="json") for project in projects],
            }
            await db.commit()
            await db.refresh(snapshot, attribute_names=["tasks"])
            if len(snapshot.tasks) != len(tasks):
                raise CompanyBrainServiceError(
                    category="operations_snapshot_readback_mismatch",
                    safe_detail="Operations snapshot could not be verified safely.",
                )
            return self.response(snapshot)

    async def _fail_snapshot(
        self,
        snapshot_id: UUID,
        trigger: str,
        category: str,
        safe_error: str,
        metrics: dict[str, object] | None = None,
    ) -> None:
        async with AsyncSessionLocal() as db:
            snapshot = await db.get(OperationsSnapshot, snapshot_id)
            if snapshot is not None:
                snapshot.status = "failed"
                snapshot.failed_at = _utcnow()
                snapshot.error_category = category
                snapshot.safe_error = safe_error
                snapshot.metadata_json = {
                    "sync_trigger": trigger,
                    **(metrics or {}),
                }
                await db.commit()

    async def sync(
        self,
        trigger: str,
        *,
        allow_empty: bool = False,
    ) -> OperationsSnapshotResponse:
        if self._sync_lock.locked():
            raise OperationsSyncInProgressError()
        await self.recover_stale_running()
        if self._sync_lock.locked() or await self.has_persisted_running():
            raise OperationsSyncInProgressError()

        async with self._sync_lock:
            started_at = _utcnow()
            snapshot_id = await self._create_running_snapshot(trigger, started_at)

            sync_started = perf_counter()
            safe_metrics: dict[str, object] = {}
            try:
                tasks, projects = await asyncio.wait_for(
                    asyncio.gather(
                        connector_manager.tasks("monday"),
                        connector_manager.projects("monday"),
                    ),
                    timeout=settings.operations_sync_timeout_seconds,
                )
                deduplicated = {task.external_id: task for task in tasks}
                normalized_tasks = [deduplicated[key] for key in sorted(deduplicated)]
                try:
                    connector_metrics = connector_manager.task_fetch_diagnostics("monday")
                except ConnectorError:
                    connector_metrics = {}
                safe_metrics = {
                    "boards_requested": connector_metrics.get("boards_requested"),
                    "boards_returned": len(projects),
                    "groups_returned": connector_metrics.get("groups_returned"),
                    "raw_items_count": connector_metrics.get("raw_items_count", len(tasks)),
                    "normalized_tasks_count": len(normalized_tasks),
                    "skipped_items_count": connector_metrics.get("skipped_items_count", 0),
                    "skip_reason_counts": connector_metrics.get("skip_reason_counts", {}),
                    "snapshot_task_count": len(normalized_tasks),
                }
                if projects and not normalized_tasks and not allow_empty:
                    previous = await self.get_snapshot_response()
                    safe_metrics["previous_successful_snapshot_task_count"] = (
                        previous.task_count
                    )
                    if previous.snapshot_id is not None and previous.task_count > 0:
                        safe_metrics["empty_snapshot_rejected"] = True
                        await self._fail_snapshot(
                            snapshot_id,
                            trigger,
                            "operations_sync_empty_result",
                            OperationsSyncEmptyResultError.safe_detail,
                            safe_metrics,
                        )
                        performance_logger.info(
                            {
                                "event": "operations_sync_performance",
                                "operations_sync_trigger": trigger,
                                "operations_sync_status": "suspicious_empty",
                                "operations_sync_error_category": "operations_sync_empty_result",
                                "operations_snapshot_id": str(snapshot_id),
                                **safe_metrics,
                            }
                        )
                        raise OperationsSyncEmptyResultError(previous)
                safe_metrics.setdefault("previous_successful_snapshot_task_count", 0)
                safe_metrics.setdefault("empty_snapshot_rejected", False)

                result = await self._complete_snapshot(
                    snapshot_id,
                    normalized_tasks,
                    projects,
                    trigger,
                    sync_started,
                )
                performance_logger.info(
                    {
                        "event": "operations_sync_performance",
                        "operations_sync_trigger": trigger,
                        "operations_sync_status": "success",
                        "operations_sync_error_category": None,
                        "operations_live_sync_duration_ms": round(
                            (perf_counter() - sync_started) * 1000, 3
                        ),
                        "operations_snapshot_id": str(result.snapshot_id),
                        "operations_snapshot_task_count": result.task_count,
                        **safe_metrics,
                    }
                )
                return result
            except asyncio.CancelledError:
                await asyncio.shield(
                    self._fail_snapshot(
                        snapshot_id,
                        trigger,
                        "operations_sync_cancelled",
                        "Operations refresh was cancelled safely.",
                    )
                )
                performance_logger.info(
                    {
                        "event": "operations_sync_performance",
                        "operations_sync_trigger": trigger,
                        "operations_sync_status": "cancelled",
                        "operations_sync_error_category": "operations_sync_cancelled",
                        "operations_snapshot_id": str(snapshot_id),
                        "operations_snapshot_task_count": 0,
                    }
                )
                raise
            except Exception as exc:
                if isinstance(exc, OperationsSyncEmptyResultError):
                    raise
                category = (
                    "operations_sync_timeout"
                    if isinstance(exc, TimeoutError)
                    else "operations_sync_failed"
                )
                safe_error = (
                    "Operations refresh timed out."
                    if isinstance(exc, TimeoutError)
                    else "Operations refresh failed. Existing snapshot data remains available."
                )
                await self._fail_snapshot(
                    snapshot_id,
                    trigger,
                    category,
                    safe_error,
                    safe_metrics,
                )
                performance_logger.info(
                    {
                        "event": "operations_sync_performance",
                        "operations_sync_trigger": trigger,
                        "operations_sync_status": "failed",
                        "operations_sync_error_category": category,
                        "operations_live_sync_duration_ms": round(
                            (perf_counter() - sync_started) * 1000, 3
                        ),
                        "operations_snapshot_id": str(snapshot_id),
                        "operations_snapshot_task_count": 0,
                        **safe_metrics,
                    }
                )
                if isinstance(exc, ConnectorError):
                    raise CompanyBrainServiceError(
                        category=category,
                        safe_detail=safe_error,
                    ) from exc
                raise CompanyBrainServiceError(
                    category=category,
                    status_code=504 if isinstance(exc, TimeoutError) else 503,
                    safe_detail=safe_error,
                ) from exc

    async def status(self) -> OperationsSyncStatusResponse:
        stale_running_recovered = await self.recover_stale_running()
        async with AsyncSessionLocal() as db:
            latest_success = await self._latest(db, "success")
            latest_failure = await self._latest(db, "failed")
            latest_running = await self._latest(db, "running")
        freshness, age = self.freshness(latest_success)
        running = self.sync_running or latest_running is not None
        failure_is_latest = bool(
            latest_failure
            and (
                latest_success is None
                or latest_failure.created_at > latest_success.created_at
            )
        )
        if running:
            status = "running"
        elif failure_is_latest:
            status = (
                "suspicious_empty"
                if latest_failure.error_category == "operations_sync_empty_result"
                else "failed"
            )
        elif freshness == "stale":
            status = "stale"
        elif latest_success is not None:
            status = "success"
        else:
            status = "idle"
        return OperationsSyncStatusResponse(
            state="running" if running else "idle",
            running=running,
            status=status,
            started_at=latest_running.started_at if running and latest_running else None,
            last_success_at=latest_success.fetched_at if latest_success else None,
            last_failure_at=latest_failure.failed_at if latest_failure else None,
            latest_snapshot_id=latest_success.id if latest_success else None,
            latest_snapshot_age_seconds=age,
            latest_snapshot_status=("refreshing" if running else freshness),
            safe_error=latest_failure.safe_error if failure_is_latest else None,
            can_refresh=not running,
            stale_running_recovered=stale_running_recovered,
        )


operations_snapshot_service = OperationsSnapshotService()


async def operations_sync_loop(stop_event: asyncio.Event) -> None:
    trigger = "startup"
    while not stop_event.is_set():
        try:
            await operations_snapshot_service.sync(trigger)
        except CompanyBrainServiceError:
            pass
        trigger = "background"
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.operations_sync_interval_seconds,
            )
        except TimeoutError:
            continue
