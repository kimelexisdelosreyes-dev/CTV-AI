import pytest

from app.connectors.monday import MondayConnector
from app.connectors.monday_settings import MondaySettings


def test_task_normalization() -> None:
    config = MondaySettings(
        enabled=True,
        api_token="test",
        api_version="2026-07",
        board_ids=("123",),
        status_column_ids=("status",),
        priority_column_ids=("priority",),
        due_date_column_ids=("date",),
        people_column_ids=("person",),
        timeout_seconds=10,
        page_size=100,
    )
    connector = MondayConnector(config)
    item = {
        "id": "456",
        "name": "Edit documentary",
        "_board": {"id": "123", "name": "Projects"},
        "group": {"id": "g1", "title": "Production"},
        "column_values": [
            {"id":"status","type":"status","text":"Working on it","value":None,"column":{"title":"Status"}},
            {"id":"priority","type":"dropdown","text":"High","value":None,"column":{"title":"Priority"}},
            {"id":"date","type":"date","text":"2026-07-20","value":"{\"date\":\"2026-07-20\"}","column":{"title":"Deadline"}},
            {"id":"person","type":"people","text":"Kim","value":"{\"personsAndTeams\":[{\"id\":99,\"kind\":\"person\"}]}","column":{"title":"Person"}},
        ],
    }
    task = connector._normalize(item)
    assert task.title == "Edit documentary"
    assert task.status == "Working on it"
    assert task.priority == "High"
    assert task.assignee_ids == ["99"]
    assert task.project_id == "123"
    assert task.due_at is not None


@pytest.mark.anyio
async def test_task_pagination_and_structural_diagnostics(monkeypatch) -> None:
    config = MondaySettings(
        enabled=True,
        api_token="test",
        api_version="2026-07",
        board_ids=("123",),
        status_column_ids=(),
        priority_column_ids=(),
        due_date_column_ids=(),
        people_column_ids=(),
        timeout_seconds=10,
        page_size=1,
    )
    connector = MondayConnector(config)
    calls = 0

    async def graphql(_query, _variables):
        nonlocal calls
        calls += 1
        item_id = str(calls)
        return {
            "boards": [
                {
                    "id": "123",
                    "name": "Projects",
                    "url": "https://example.invalid/board",
                    "items_page": {
                        "cursor": "next" if calls == 1 else None,
                        "items": [
                            {
                                "id": item_id,
                                "name": f"Task {item_id}",
                                "group": {"id": "group-1", "title": "This week"},
                                "column_values": [],
                            }
                        ],
                    },
                }
            ]
        }

    monkeypatch.setattr(connector, "_graphql", graphql)

    tasks = await connector.get_tasks()

    assert [item.external_id for item in tasks] == ["1", "2"]
    assert calls == 2
    assert connector.last_task_fetch_diagnostics == {
        "boards_requested": 1,
        "boards_returned": 1,
        "groups_returned": 1,
        "raw_items_count": 2,
        "normalized_tasks_count": 2,
        "skipped_items_count": 0,
        "skip_reason_counts": {},
        "pages_fetched": 2,
    }
