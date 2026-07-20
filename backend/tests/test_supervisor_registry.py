from types import SimpleNamespace

import pytest

from app.supervisor.agent_registry import AgentRegistry, AgentRegistryError
from app.supervisor.agents import build_agent_registry
from app.supervisor.schemas import AgentDefinition


def definition(agent_id="test_agent", *, enabled=True, capabilities=None):
    return AgentDefinition(
        agent_id=agent_id,
        name="Test Agent",
        description="Read-only test agent.",
        capabilities=frozenset(capabilities or {"knowledge_search"}),
        supported_intents=frozenset({"policy"}),
        required_permissions=frozenset({"knowledge.read"}),
        input_schema="TestInputV1",
        output_schema="TestOutputV1",
        estimated_cost_class="light",
        enabled=enabled,
    )


def test_initial_registry_contains_only_expected_read_only_agents() -> None:
    registry = build_agent_registry()
    assert {item.agent_id for item in registry.definitions()} == {
        "knowledge_agent",
        "operations_agent",
        "employee_agent",
        "reasoning_agent",
        "response_composer_agent",
    }
    assert registry.resolve("overdue_tasks")[0].definition.agent_id == "operations_agent"


def test_registry_rejects_duplicates_and_invalid_capabilities() -> None:
    registry = AgentRegistry()
    registry.register(SimpleNamespace(definition=definition()))
    with pytest.raises(AgentRegistryError, match="Duplicate"):
        registry.register(SimpleNamespace(definition=definition()))
    with pytest.raises(AgentRegistryError, match="capability"):
        registry.register(
            SimpleNamespace(
                definition=definition("bad_agent", capabilities={"invalid capability"})
            )
        )


def test_disabled_agent_is_not_resolved() -> None:
    registry = AgentRegistry()
    registry.register(SimpleNamespace(definition=definition(enabled=False)))
    assert registry.resolve("knowledge_search") == []
