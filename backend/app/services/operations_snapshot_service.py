import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.connectors.base import ConnectorError
from app.connectors.monday import MondayApiError
from app.connectors.manager import connector_manager
from app.connectors.models import ConnectorProject, ConnectorTask
from app.core.config import settings
from app.db.models.operations_snapshot import OperationTask, OperationsSnapshot
from app.db.session import AsyncSessionLocal, engine
from app.schemas.operations import OperationsSnapshotResponse, OperationsSyncStatusResponse
from app.services.service_errors import CompanyBrainServiceError
from app.services.semantic_cache import semantic_cache


performance_logger = logging.getLogger("ctv_one.performance")
SNAPSHOT_ADVISORY_LOCK_ID = 0x43545632


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


def operations_content_hash(
    tasks: list[ConnectorTask],
    projects: list[ConnectorProject],
) -> str:
    """Hash answer-affecting normalized fields; exclude volatile fetch timestamps."""
    normalized_tasks = [
        {
            "external_id": task.external_id,
            "title": task.title.strip(),
            "status": (task.status or "").strip(),
            "priority": (task.priority or "").strip(),
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "assignee_ids": sorted(str(item) for item in task.assignee_ids),
            "project_id": task.project_id,
            "url": task.url,
            "board_name": (task.metadata or {}).get("board_name"),
            "group_id": (task.metadata or {}).get("group_id"),
            "group_title": (task.metadata or {}).get("group_title"),
        }
        for task in sorted(tasks, key=lambda item: item.external_id)
    ]
    normalized_projects = [
        {
            "external_id": project.external_id,
            "name": project.name.strip(),
            "status": (project.status or "").strip(),
            "owner_ids": sorted(str(item) for item in project.owner_ids),
            "url": project.url,
        }
        for project in sorted(projects, key=lambda item: item.external_id)
    ]
    payload = json.dumps(
        {"tasks": normalized_tasks, "projects": normalized_projects},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class OperationsSnapshotService:
    def __init__(self) -> None:
        self._sync_lock = asyncio.Lock()

    @property
    def sync_running(self) -> bool:
        return self._sync_lock.locked()

    @asynccontextmanager
    async def _database_refresh_lock(self):
        started = perf_counter()
        connection = None
        acquired = False
        try:
            connection = await engine.connect()
            acquired = bool(
                await connection.scalar(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": SNAPSHOT_ADVISORY_LOCK_ID},
                )
            )
        except Exception:
            # Refresh writes also require PostgreSQL; the in-process guard keeps unit
            # tests and controlled startup failure paths safe until the write fails.
            performance_logger.warning(
                {
                    "event": "operations_snapshot_lock_unavailable",
                    "snapshot_lock_acquired": False,
                }
            )
            if connection is not None:
                await connection.close()
            yield True, round((perf_counter() - started) * 1000, 3)
            return
        try:
            yield acquired, round((perf_counter() - started) * 1000, 3)
        finally:
            async def release() -> None:
                try:
                    if acquired:
                        await connection.execute(
                            text("SELECT pg_advisory_unlock(:lock_id)"),
                            {"lock_id": SNAPSHOT_ADVISORY_LOCK_ID},
                        )
                except Exception:
                    performance_logger.warning(
                        {"event": "operations_snapshot_unlock_failed"}
                    )
                finally:
                    await connection.close()

            await asyncio.shield(release())

    async def _fetch_with_retries(
        self,
    ) -> tuple[list[ConnectorTask], list[ConnectorProject], int]:
        maximum = max(settings.ctv_one_monday_snapshot_retry_attempts, 1)
        for attempt in range(1, maximum + 1):
            try:
                tasks, projects = await asyncio.wait_for(
                    asyncio.gather(
                        connector_manager.tasks("monday"),
                        connector_manager.projects("monday"),
                    ),
                    timeout=settings.operations_sync_timeout_seconds,
                )
                return tasks, projects, attempt
            except Exception as exc:
                retryable = isinstance(exc, TimeoutError) or (
                    isinstance(exc, MondayApiError) and exc.retryable
                )
                if not retryable or attempt >= maximum:
                    setattr(exc, "snapshot_attempt_count", attempt)
                    raise
                configured_delay = max(
                    settings.ctv_one_monday_snapshot_retry_base_seconds
                    * (2 ** (attempt - 1)),
                    0.0,
                )
                retry_after = (
                    exc.retry_after_seconds
                    if isinstance(exc, MondayApiError)
                    else None
                )
                await asyncio.sleep(min(max(configured_delay, retry_after or 0.0), 10.0))

    async def _latest(
        self,
        db: AsyncSession,
        status: str,
        *,
        load_tasks: bool = True,
    ) -> OperationsSnapshot | None:
        statement = (
            select(OperationsSnapshot)
            .where(OperationsSnapshot.status == status)
            .order_by(
                OperationsSnapshot.fetched_at.desc().nullslast(),
                OperationsSnapshot.created_at.desc(),
            )
            .limit(1)
        )
        if load_tasks:
            statement = statement.options(selectinload(OperationsSnapshot.tasks))
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def latest_successful(self) -> OperationsSnapshot | None:
        async with AsyncSessionLocal() as db:
            return await self._latest(db, "active")

    def freshness(self, snapshot: OperationsSnapshot | None) -> tuple[str, float | None]:
        if snapshot is None or snapshot.fetched_at is None:
            return "unavailable", None
        fetched_at = snapshot.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        age = max((_utcnow() - fetched_at).total_seconds(), 0.0)
        if age <= settings.ctv_one_operations_snapshot_fresh_seconds:
            freshness = "fresh"
        elif age <= settings.ctv_one_operations_snapshot_aging_seconds:
            freshness = "aging"
        else:
            freshness = "stale"
        return freshness, round(age, 3)

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
                status="unavailable",
                freshness="unavailable",
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
            generated_at=getattr(snapshot, "generated_at", None),
            activated_at=getattr(snapshot, "activated_at", None),
            age_seconds=age,
            task_count=snapshot.task_count,
            board_count=getattr(snapshot, "board_count", 0),
            content_hash_prefix=(getattr(snapshot, "content_hash", None) or "")[:12] or None,
            content_hash=getattr(snapshot, "content_hash", None),
            content_changed=getattr(snapshot, "content_changed", None),
            semantic_cache_invalidated=getattr(
                snapshot, "semantic_cache_invalidated", False
            ),
            cache_invalidation_count=getattr(snapshot, "cache_invalidation_count", 0),
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
                    OperationsSnapshot.status.in_(("pending", "running"))
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
            pending = await self._latest(db, "pending", load_tasks=False)
            return pending is not None or await self._latest(
                db, "running", load_tasks=False
            ) is not None

    async def _create_running_snapshot(
        self,
        trigger: str,
        started_at: datetime,
        triggered_by: str | None = None,
    ) -> UUID:
        async with AsyncSessionLocal() as db:
            snapshot = OperationsSnapshot(
                source="monday",
                status="pending",
                started_at=started_at,
                triggered_by=triggered_by,
                trigger_type=trigger,
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
        content_hash = operations_content_hash(tasks, projects)
        now = _utcnow()
        duration_ms = round((perf_counter() - sync_started) * 1000, 3)
        previous_hash = None
        try:
            source_item_count = int(
                connector_manager.task_fetch_diagnostics("monday").get(
                    "raw_items_count", len(tasks)
                )
            )
        except (ConnectorError, TypeError, ValueError):
            source_item_count = len(tasks)
        async with AsyncSessionLocal() as db:
            snapshot = await db.get(
                OperationsSnapshot,
                snapshot_id,
                options=[selectinload(OperationsSnapshot.tasks)],
            )
            if snapshot is None:
                raise OperationsSnapshotUnavailableError()
            previous = await self._latest(db, "active", load_tasks=False)
            previous_hash = previous.content_hash if previous else None
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
            if previous is not None and previous.id != snapshot.id:
                previous.status = "retired"
                # This flush remains inside the activation transaction. It orders
                # the immediate partial-unique check without exposing retirement.
                await db.flush()
            snapshot.status = "active"
            snapshot.fetched_at = now
            snapshot.generated_at = now
            snapshot.activated_at = now
            snapshot.completed_at = now
            snapshot.task_count = len(tasks)
            snapshot.board_count = len(projects)
            snapshot.source_item_count = source_item_count
            snapshot.refresh_duration_ms = duration_ms
            snapshot.attempt_count = int(getattr(self, "_current_attempt_count", 1))
            snapshot.trigger_type = trigger
            snapshot.previous_snapshot_id = previous.id if previous else None
            snapshot.content_hash = content_hash
            snapshot.content_changed = previous_hash != content_hash
            snapshot.metadata_json = {
                "sync_trigger": trigger,
                "sync_duration_ms": duration_ms,
                "projects": [project.model_dump(mode="json") for project in projects],
            }
            await db.commit()

        invalidated = 0
        cache_invalidated = False
        if previous_hash != content_hash:
            try:
                invalidated = await semantic_cache.invalidate_operations()
                cache_invalidated = True
            except Exception:
                performance_logger.warning(
                    {
                        "event": "operations_cache_invalidation_failed",
                        "operations_snapshot_id": str(snapshot_id),
                    }
                )
        async with AsyncSessionLocal() as db:
            snapshot = await db.get(
                OperationsSnapshot,
                snapshot_id,
                options=[selectinload(OperationsSnapshot.tasks)],
            )
            if snapshot is None:
                raise OperationsSnapshotUnavailableError()
            snapshot.semantic_cache_invalidated = cache_invalidated
            snapshot.cache_invalidation_count = invalidated
            metadata = dict(snapshot.metadata_json or {})
            metadata.update(
                {
                    "operations_cache_invalidated": cache_invalidated,
                    "operations_cache_invalidated_entries": invalidated,
                    "operations_snapshot_content_changed": previous_hash
                    != content_hash,
                }
            )
            snapshot.metadata_json = metadata
            await db.commit()
            await db.refresh(snapshot, attribute_names=["tasks"])
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
                snapshot.completed_at = snapshot.failed_at
                snapshot.trigger_type = trigger
                snapshot.attempt_count = int(
                    (metrics or {}).get("snapshot_refresh_attempt_count", 0) or 0
                )
                snapshot.refresh_duration_ms = (
                    (metrics or {}).get("snapshot_refresh_duration_ms")
                )
                snapshot.content_changed = False
                snapshot.semantic_cache_invalidated = False
                snapshot.cache_invalidation_count = 0
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
        triggered_by: str | None = None,
    ) -> OperationsSnapshotResponse:
        if self._sync_lock.locked():
            raise OperationsSyncInProgressError()
        await self.recover_stale_running()
        if self._sync_lock.locked() or await self.has_persisted_running():
            raise OperationsSyncInProgressError()

        async with self._sync_lock:
            async with self._database_refresh_lock() as (acquired, lock_wait_ms):
                if not acquired:
                    raise OperationsSyncInProgressError()
                return await self._run_sync(
                    trigger,
                    allow_empty=allow_empty,
                    lock_wait_ms=lock_wait_ms,
                    triggered_by=triggered_by,
                )

    async def _run_sync(
        self,
        trigger: str,
        *,
        allow_empty: bool,
        lock_wait_ms: float,
        triggered_by: str | None,
    ) -> OperationsSnapshotResponse:
        started_at = _utcnow()
        snapshot_id = await self._create_running_snapshot(
            trigger, started_at, triggered_by
        )
        sync_started = perf_counter()
        safe_metrics: dict[str, object] = {
            "snapshot_refresh_started": True,
            "snapshot_lock_wait_ms": lock_wait_ms,
            "snapshot_lock_acquired": True,
        }
        try:
            tasks, projects, attempt_count = await self._fetch_with_retries()
            deduplicated = {task.external_id: task for task in tasks}
            normalized_tasks = [deduplicated[key] for key in sorted(deduplicated)]
            try:
                connector_metrics = connector_manager.task_fetch_diagnostics("monday")
            except ConnectorError:
                connector_metrics = {}
            safe_metrics.update(
                {
                    "snapshot_refresh_attempt_count": attempt_count,
                    "boards_requested": connector_metrics.get("boards_requested"),
                    "boards_returned": len(projects),
                    "groups_returned": connector_metrics.get("groups_returned"),
                    "raw_items_count": connector_metrics.get(
                        "raw_items_count", len(tasks)
                    ),
                    "normalized_tasks_count": len(normalized_tasks),
                    "skipped_items_count": connector_metrics.get(
                        "skipped_items_count", 0
                    ),
                    "skip_reason_counts": connector_metrics.get(
                        "skip_reason_counts", {}
                    ),
                    "snapshot_task_count": len(normalized_tasks),
                }
            )
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
                    self._log_refresh(
                        "suspicious_empty", snapshot_id, sync_started, safe_metrics
                    )
                    raise OperationsSyncEmptyResultError(previous)
            safe_metrics.setdefault("previous_successful_snapshot_task_count", 0)
            safe_metrics.setdefault("empty_snapshot_rejected", False)
            self._current_attempt_count = attempt_count
            result = await self._complete_snapshot(
                snapshot_id,
                normalized_tasks,
                projects,
                trigger,
                sync_started,
            )
            safe_metrics.update(
                {
                    "snapshot_refresh_completed": True,
                    "snapshot_content_changed": result.content_changed,
                    "snapshot_active_id": str(result.snapshot_id),
                    "operations_cache_invalidated": result.semantic_cache_invalidated,
                    "cache_invalidation_count": result.cache_invalidation_count,
                }
            )
            self._log_refresh("success", snapshot_id, sync_started, safe_metrics)
            return result
        except asyncio.CancelledError:
            await asyncio.shield(
                self._fail_snapshot(
                    snapshot_id,
                    trigger,
                    "operations_sync_cancelled",
                    "Operations refresh was cancelled safely.",
                    safe_metrics,
                )
            )
            self._log_refresh("cancelled", snapshot_id, sync_started, safe_metrics)
            raise
        except Exception as exc:
            if isinstance(exc, OperationsSyncEmptyResultError):
                raise
            attempt_count = int(getattr(exc, "snapshot_attempt_count", 1))
            if isinstance(exc, TimeoutError):
                category = "operations_sync_timeout"
                safe_error = "Operations refresh timed out."
            elif isinstance(exc, MondayApiError):
                category = exc.category
                safe_error = exc.safe_detail
            else:
                category = "operations_sync_failed"
                safe_error = (
                    "Operations refresh failed. Existing snapshot data remains available."
                )
            safe_metrics.update(
                {
                    "snapshot_refresh_failed": True,
                    "snapshot_refresh_attempt_count": attempt_count,
                    "snapshot_refresh_duration_ms": round(
                        (perf_counter() - sync_started) * 1000, 3
                    ),
                    "cache_invalidation_count": 0,
                }
            )
            await self._fail_snapshot(
                snapshot_id,
                trigger,
                category,
                safe_error,
                safe_metrics,
            )
            self._log_refresh("failed", snapshot_id, sync_started, safe_metrics, category)
            raise CompanyBrainServiceError(
                category=category,
                status_code=504 if isinstance(exc, TimeoutError) else 503,
                safe_detail=safe_error,
            ) from exc

    def _log_refresh(
        self,
        status: str,
        snapshot_id: UUID,
        sync_started: float,
        metrics: dict[str, object],
        category: str | None = None,
    ) -> None:
        performance_logger.info(
            {
                "event": "operations_sync_performance",
                "operations_sync_status": status,
                "operations_sync_error_category": category,
                "snapshot_refresh_duration_ms": round(
                    (perf_counter() - sync_started) * 1000, 3
                ),
                "operations_snapshot_id": str(snapshot_id),
                **metrics,
            }
        )

    async def status(self) -> OperationsSyncStatusResponse:
        stale_running_recovered = await self.recover_stale_running()
        async with AsyncSessionLocal() as db:
            latest_success = await self._latest(db, "active", load_tasks=False)
            latest_failure = await self._latest(db, "failed", load_tasks=False)
            latest_running = await self._latest(db, "pending", load_tasks=False)
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
        elif freshness == "aging":
            status = "aging"
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
            active_snapshot_id=latest_success.id if latest_success else None,
            generated_at=latest_success.generated_at if latest_success else None,
            activated_at=latest_success.activated_at if latest_success else None,
            task_count=latest_success.task_count if latest_success else 0,
            board_count=latest_success.board_count if latest_success else 0,
            content_hash_prefix=(latest_success.content_hash or "")[:12]
            if latest_success
            else None,
            last_refresh_status=(
                latest_failure.status if failure_is_latest else latest_success.status
                if latest_success
                else None
            ),
            last_refresh_duration_ms=(
                latest_failure.refresh_duration_ms
                if failure_is_latest
                else latest_success.refresh_duration_ms if latest_success else None
            ),
            last_failure_category=(
                latest_failure.error_category if latest_failure else None
            ),
            refresh_currently_running=running,
            semantic_cache_invalidated=(
                latest_success.semantic_cache_invalidated if latest_success else False
            ),
            cache_invalidation_count=(
                latest_success.cache_invalidation_count if latest_success else 0
            ),
            content_changed=(latest_success.content_changed if latest_success else None),
        )


operations_snapshot_service = OperationsSnapshotService()


async def operations_sync_loop(stop_event: asyncio.Event) -> None:
    if not settings.ctv_one_monday_snapshot_refresh_on_startup:
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.ctv_one_monday_snapshot_refresh_interval_seconds,
            )
            return
        except TimeoutError:
            pass
    trigger = "startup" if settings.ctv_one_monday_snapshot_refresh_on_startup else "scheduled"
    while not stop_event.is_set():
        try:
            await operations_snapshot_service.sync(trigger)
        except Exception:
            performance_logger.warning(
                {
                    "event": "operations_snapshot_scheduler_failure",
                    "operations_sync_trigger": trigger,
                }
            )
        trigger = "scheduled"
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.ctv_one_monday_snapshot_refresh_interval_seconds,
            )
        except TimeoutError:
            continue
