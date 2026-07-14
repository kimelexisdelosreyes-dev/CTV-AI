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
