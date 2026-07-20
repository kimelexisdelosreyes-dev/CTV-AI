from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.connectors.models import ConnectorProject, ConnectorTask


Freshness = Literal[
    "fresh", "aging", "stale", "unavailable", "refreshing", "empty", "failed"
]


class OperationsSnapshotResponse(BaseModel):
    snapshot_id: UUID | None
    source: str = "monday"
    status: str
    freshness: Freshness
    fetched_at: datetime | None
    generated_at: datetime | None = None
    activated_at: datetime | None = None
    age_seconds: float | None
    task_count: int
    board_count: int = 0
    content_hash_prefix: str | None = None
    content_hash: str | None = Field(default=None, exclude=True)
    content_changed: bool | None = None
    semantic_cache_invalidated: bool = False
    cache_invalidation_count: int = 0
    tasks: list[ConnectorTask] = Field(default_factory=list)
    projects: list[ConnectorProject] = Field(default_factory=list)
    safe_error: str | None = None


class OperationsSyncStatusResponse(BaseModel):
    state: Literal["idle", "running"]
    running: bool
    status: Literal[
        "idle", "running", "success", "failed", "aging", "stale", "suspicious_empty"
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
    active_snapshot_id: UUID | None = None
    generated_at: datetime | None = None
    activated_at: datetime | None = None
    task_count: int = 0
    board_count: int = 0
    content_hash_prefix: str | None = None
    last_refresh_status: str | None = None
    last_refresh_duration_ms: float | None = None
    last_failure_category: str | None = None
    refresh_currently_running: bool = False
    semantic_cache_invalidated: bool = False
    cache_invalidation_count: int = 0
    content_changed: bool | None = None


class OperationsRefreshResponse(BaseModel):
    status: Literal["running", "success", "suspicious_empty"]
    message: str
    running: bool
    snapshot: OperationsSnapshotResponse
