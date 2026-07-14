from datetime import datetime, timezone

from app.connectors.models import ConnectorTask
from app.services.operations_context_service import (
    _done,
    _due_today,
    _overdue,
    _question_is_operational,
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
