from datetime import datetime, timezone

import pytest

from app.connectors.models import ConnectorTask
from app.services.operations_context_service import (
    _done,
    _due_today,
    _overdue,
    _question_is_operational,
    operations_context_service,
)


def test_operational_intent_detection() -> None:
    assert _question_is_operational("What tasks are overdue?")
    assert _question_is_operational("What should we prioritize today?")
    assert not _question_is_operational("What is our leave policy?")


def test_task_status_helpers() -> None:
    now = datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)

    done = ConnectorTask(
        external_id="1",
        title="Finished task",
        status="Done",
        due_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    overdue = ConnectorTask(
        external_id="2",
        title="Late task",
        status="Working on it",
        due_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    today = ConnectorTask(
        external_id="3",
        title="Today's task",
        status="Working on it",
        due_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert _done(done.status)
    assert not _overdue(done, now)
    assert _overdue(overdue, now)
    assert _due_today(today, now)


async def _projects(_connector):
    return []


def task(
    external_id: str,
    title: str,
    status: str = "Working on it",
    priority: str | None = None,
    due_at: datetime | None = None,
) -> ConnectorTask:
    return ConnectorTask(
        external_id=external_id,
        title=title,
        status=status,
        priority=priority,
        due_at=due_at,
        metadata={"board_name": "Ops", "group_title": "This week"},
    )


@pytest.mark.anyio
async def test_overdue_context_filters_to_overdue_tasks(monkeypatch) -> None:
    now_past = datetime(2026, 7, 1, tzinfo=timezone.utc)
    now_future = datetime(2026, 7, 30, tzinfo=timezone.utc)

    async def fake_tasks(_connector):
        return [
            task("1", "Late invoice", due_at=now_past),
            task("2", "Future shoot", due_at=now_future),
            task("3", "Completed late", status="Done", due_at=now_past),
        ]

    monkeypatch.setattr(
        "app.services.operations_context_service.connector_manager.tasks",
        fake_tasks,
    )
    monkeypatch.setattr(
        "app.services.operations_context_service.connector_manager.projects",
        _projects,
    )

    context = await operations_context_service.build(
        "Which tasks are overdue?",
        max_tasks=5,
        max_chars=2000,
        force=True,
    )

    assert context.task_count == 1
    assert context.original_task_count == 1
    assert "Late invoice" in context.text
    assert "Future shoot" not in context.text
    assert "Completed late" not in context.text


@pytest.mark.anyio
async def test_operations_priorities_ranks_and_caps_tasks(monkeypatch) -> None:
    async def fake_tasks(_connector):
        return [
            task("1", "Normal task"),
            task("2", "Blocked delivery", status="Blocked", priority="High"),
            task("3", "Urgent client issue", priority="Urgent"),
        ]

    monkeypatch.setattr(
        "app.services.operations_context_service.connector_manager.tasks",
        fake_tasks,
    )
    monkeypatch.setattr(
        "app.services.operations_context_service.connector_manager.projects",
        _projects,
    )

    context = await operations_context_service.build(
        "What are the highest operational priorities?",
        max_tasks=2,
        max_chars=2000,
        force=True,
    )

    assert context.task_count == 2
    assert context.original_task_count == 3
    assert "Urgent client issue" in context.text
    assert "Blocked delivery" in context.text
    assert "Normal task" not in context.text
