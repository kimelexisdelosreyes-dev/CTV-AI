from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConnectorCapability(str, Enum):
    health = "health"
    identity = "identity"
    tasks = "tasks"
    projects = "projects"
    search = "search"
    actions = "actions"
    webhooks = "webhooks"


class ConnectorStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unavailable = "unavailable"
    disabled = "disabled"


class ConnectorDescriptor(BaseModel):
    name: str
    display_name: str
    enabled: bool
    capabilities: list[ConnectorCapability]
    description: str | None = None


class ConnectorHealth(BaseModel):
    name: str
    status: ConnectorStatus
    checked_at: datetime
    latency_ms: float | None = None
    detail: str | None = None


class ConnectorIdentity(BaseModel):
    external_user_id: str
    display_name: str | None = None
    email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorTask(BaseModel):
    external_id: str
    title: str
    status: str | None = None
    priority: str | None = None
    due_at: datetime | None = None
    assignee_ids: list[str] = Field(default_factory=list)
    project_id: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorProject(BaseModel):
    external_id: str
    name: str
    status: str | None = None
    owner_ids: list[str] = Field(default_factory=list)
    start_at: datetime | None = None
    due_at: datetime | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=5000)
    limit: int = Field(default=10, ge=1, le=100)


class ConnectorSearchResult(BaseModel):
    connector: str
    result_type: str
    external_id: str
    title: str
    snippet: str | None = None
    url: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
