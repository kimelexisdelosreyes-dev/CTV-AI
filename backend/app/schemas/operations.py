from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.connectors.models import ConnectorProject, ConnectorTask


Freshness = Literal["fresh", "stale", "refreshing", "failed", "empty"]


class OperationsSnapshotResponse(BaseModel):
    snapshot_id: UUID | None
    source: str = "monday"
    status: str
    freshness: Freshness
    fetched_at: datetime | None
    age_seconds: float | None
    task_count: int
    tasks: list[ConnectorTask] = Field(default_factory=list)
    projects: list[ConnectorProject] = Field(default_factory=list)
    safe_error: str | None = None


class OperationsSyncStatusResponse(BaseModel):
    state: Literal["idle", "running"]
    running: bool
    status: Literal[
        "idle", "running", "success", "failed", "stale", "suspicious_empty"
    ]
    started_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    latest_snapshot_id: UUID | None
    latest_snapshot_age_seconds: float | None
    latest_snapshot_status: Freshness
    safe_error: str | None
    can_refresh: bool
    stale_running_recovered: bool = False


class OperationsRefreshResponse(BaseModel):
    status: Literal["running", "success", "suspicious_empty"]
    message: str
    running: bool
    snapshot: OperationsSnapshotResponse
