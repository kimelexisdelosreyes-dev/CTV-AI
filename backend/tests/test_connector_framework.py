import pytest

from app.connectors.manager import connector_manager
from app.connectors.mock import MockConnector
from app.connectors.registry import connector_registry


@pytest.mark.asyncio
async def test_mock_connector_framework() -> None:
    connector_registry.clear()
    connector_registry.register(MockConnector())

    descriptors = connector_manager.descriptors()
    assert descriptors[0].name == "mock"

    health = await connector_manager.health()
    assert health[0].status.value == "healthy"

    tasks = await connector_manager.tasks("mock", "user@example.com")
    assert tasks
    assert tasks[0].assignee_ids == ["user@example.com"]

    projects = await connector_manager.projects("mock")
    assert projects
