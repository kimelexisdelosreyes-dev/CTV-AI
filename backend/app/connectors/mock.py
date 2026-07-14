from datetime import datetime, timedelta, timezone
from time import perf_counter

from app.connectors.base import BaseConnector
from app.connectors.models import (
    ConnectorCapability,
    ConnectorHealth,
    ConnectorIdentity,
    ConnectorProject,
    ConnectorSearchResult,
    ConnectorStatus,
    ConnectorTask,
)


class MockConnector(BaseConnector):
    name = "mock"
    display_name = "Mock Connector"
    description = "Local connector used to validate the connector framework."
    capabilities = {
        ConnectorCapability.health,
        ConnectorCapability.identity,
        ConnectorCapability.tasks,
        ConnectorCapability.projects,
        ConnectorCapability.search,
    }

    async def health(self) -> ConnectorHealth:
        started = perf_counter()
        return ConnectorHealth(
            name=self.name,
            status=ConnectorStatus.healthy,
            checked_at=datetime.now(timezone.utc),
            latency_ms=(perf_counter() - started) * 1000,
            detail="Connector framework operational.",
        )

    async def get_identity(self, user_email: str) -> ConnectorIdentity:
        return ConnectorIdentity(
            external_user_id=user_email.lower(),
            display_name=user_email.split("@")[0],
            email=user_email.lower(),
        )

    async def get_tasks(
        self,
        external_user_id: str | None = None,
    ) -> list[ConnectorTask]:
        now = datetime.now(timezone.utc)

        return [
            ConnectorTask(
                external_id="task-001",
                title="Review Company Brain test results",
                status="Working on it",
                priority="High",
                due_at=now + timedelta(days=1),
                assignee_ids=[external_user_id] if external_user_id else [],
                project_id="project-001",
            ),
            ConnectorTask(
                external_id="task-002",
                title="Prepare monday.com connector mapping",
                status="Not started",
                priority="Medium",
                due_at=now + timedelta(days=3),
                assignee_ids=[external_user_id] if external_user_id else [],
                project_id="project-001",
            ),
        ]

    async def get_projects(self) -> list[ConnectorProject]:
        now = datetime.now(timezone.utc)

        return [
            ConnectorProject(
                external_id="project-001",
                name="CTV ONE Platform",
                status="Active",
                start_at=now - timedelta(days=30),
                due_at=now + timedelta(days=60),
            )
        ]

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ConnectorSearchResult]:
        haystack = [
            ConnectorSearchResult(
                connector=self.name,
                result_type="task",
                external_id="task-001",
                title="Review Company Brain test results",
                snippet="Validate grounded answers and employee personalization.",
                score=0.95,
            ),
            ConnectorSearchResult(
                connector=self.name,
                result_type="project",
                external_id="project-001",
                title="CTV ONE Platform",
                snippet="Local enterprise AI platform and connector framework.",
                score=0.90,
            ),
        ]

        lowered = query.lower()

        return [
            result
            for result in haystack
            if lowered in (
                f"{result.title} {result.snippet or ''}".lower()
            )
        ][:limit]
