from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.agents.capabilities import CapabilityCatalog, build_core_capability_catalog
from app.agents.errors import AgentRegistrationError, AgentRuntimeError
from app.agents.models import (
    AgentDefinition,
    AgentExecutionBudget,
    AgentHealth,
    AgentLifecycleState,
    CapabilityDefinition,
)
from app.agents.plugins import AgentPlugin, PluginRegistry
from app.agents.registry import AgentRegistry
from app.agents.runtime_manager import AgentRuntimeManager
from app.agents.context import AgentExecutionContext, AgentRuntimeServices
from app.core.config import settings
from app.supervisor.execution_engine import ExecutionEngine
from app.supervisor.schemas import AgentResult, AgentTask, ExecutionPlan


class HealthyAgent:
    def __init__(self, agent_id="test_agent", *, required=False):
        self.definition = AgentDefinition(
            agent_id=agent_id,
            display_name="Test Agent",
            description="Conformance fixture.",
            version="1.2.3",
            capabilities=frozenset({"knowledge_search"}),
            supported_intents=frozenset({"policy"}),
            required_permissions=frozenset({"knowledge.read"}),
            required=required,
            input_schema_version="KnowledgeCapabilityInputV1",
            output_schema_version="KnowledgeEvidenceV1",
            estimated_cost_class="light",
        )
        self.initialized = 0
        self.stopped = 0

    async def initialize(self, _context):
        self.initialized += 1

    async def health_check(self):
        return AgentHealth(status="healthy", safe_message="healthy")

    async def execute(self, task, context):
        return None

    async def shutdown(self):
        self.stopped += 1


class FailingAgent(HealthyAgent):
    async def initialize(self, _context):
        raise RuntimeError("private failure")


def manager_for(*agents):
    catalog = build_core_capability_catalog()
    registry = AgentRegistry(catalog)
    for agent in agents:
        registry.register(agent)
    return AgentRuntimeManager(registry, catalog, PluginRegistry(set()))


def test_definition_is_immutable_and_semver_is_validated() -> None:
    agent = HealthyAgent()
    with pytest.raises(ValidationError):
        agent.definition.version = "2.0.0"
    with pytest.raises(ValidationError):
        AgentDefinition(
            **{
                **agent.definition.model_dump(),
                "agent_id": "bad_version",
                "version": "version-one",
            }
        )


def test_catalog_rejects_duplicate_and_side_effect_capabilities() -> None:
    catalog = CapabilityCatalog()
    definition = CapabilityDefinition(
        capability_id="read_fixture",
        description="fixture",
        input_schema="InputV1",
        output_schema="OutputV1",
        required_permissions=frozenset(),
    )
    catalog.register(definition)
    with pytest.raises(AgentRegistrationError, match="Duplicate"):
        catalog.register(definition)
    with pytest.raises(AgentRegistrationError, match="read-only"):
        catalog.register(
            definition.model_copy(
                update={"capability_id": "write_fixture", "external_side_effects": True}
            )
        )


def test_registry_rejects_unknown_capability_and_permission_downgrade() -> None:
    catalog = build_core_capability_catalog()
    registry = AgentRegistry(catalog)
    unknown = HealthyAgent()
    unknown.definition = unknown.definition.model_copy(
        update={"agent_id": "unknown_agent", "capabilities": frozenset({"unknown"})}
    )
    with pytest.raises(AgentRegistrationError, match="Unknown capability"):
        registry.register(unknown)
    weak = HealthyAgent("weak_agent")
    weak.definition = weak.definition.model_copy(update={"required_permissions": frozenset()})
    with pytest.raises(AgentRegistrationError, match="permissions"):
        registry.register(weak)


@pytest.mark.asyncio
async def test_lifecycle_initialization_shutdown_and_invalid_transition(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)
    agent = HealthyAgent()
    manager = manager_for(agent)
    await manager.initialize()
    assert agent.initialized == 1
    assert manager.state_for("test_agent") == AgentLifecycleState.READY
    with pytest.raises(ValueError, match="Invalid"):
        manager.transition("test_agent", AgentLifecycleState.INITIALIZING)
    await manager.shutdown()
    await manager.shutdown()
    assert agent.stopped == 1
    assert manager.state_for("test_agent") == AgentLifecycleState.STOPPED


@pytest.mark.asyncio
async def test_optional_initialization_failure_is_isolated(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)
    manager = manager_for(FailingAgent())
    await manager.initialize()
    assert manager.state_for("test_agent") == AgentLifecycleState.FAILED


@pytest.mark.asyncio
async def test_required_initialization_failure_is_fatal(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)
    manager = manager_for(FailingAgent(required=True))
    with pytest.raises(AgentRuntimeError):
        await manager.initialize()


@pytest.mark.asyncio
async def test_health_failure_threshold_and_recovery(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)
    monkeypatch.setattr(settings, "ctv_one_agent_failure_threshold", 2)
    monkeypatch.setattr(settings, "ctv_one_agent_recovery_success_threshold", 2)
    agent = HealthyAgent()
    manager = manager_for(agent)
    await manager.initialize()

    async def fail():
        raise RuntimeError("secret")

    agent.health_check = fail
    await manager.health_check("test_agent")
    assert manager.state_for("test_agent") == AgentLifecycleState.DEGRADED
    await manager.health_check("test_agent")
    assert manager.state_for("test_agent") == AgentLifecycleState.UNAVAILABLE
    agent.health_check = lambda: _healthy()
    await manager.health_check("test_agent")
    await manager.health_check("test_agent")
    assert manager.state_for("test_agent") == AgentLifecycleState.READY


async def _healthy():
    return AgentHealth(status="healthy")


@pytest.mark.asyncio
async def test_disabled_agent_does_not_initialize(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)
    monkeypatch.setattr(settings, "ctv_one_agent_knowledge_enabled", False)
    agent = HealthyAgent(agent_id="knowledge_agent")
    manager = manager_for(agent)
    await manager.initialize()
    assert agent.initialized == 0
    assert manager.state_for("knowledge_agent") == AgentLifecycleState.DISABLED
    with pytest.raises(AgentRuntimeError):
        await manager.begin_execution("knowledge_agent")


@pytest.mark.asyncio
async def test_deterministic_resolution_excludes_degraded_when_ready_fallback_exists(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)
    primary = HealthyAgent("primary_agent")
    primary.definition = primary.definition.model_copy(update={"priority": 10})
    fallback = HealthyAgent("fallback_agent")
    fallback.definition = fallback.definition.model_copy(update={"priority": 20})
    manager = manager_for(primary, fallback)
    await manager.initialize()
    manager.transition("primary_agent", AgentLifecycleState.DEGRADED)
    resolution = manager.resolve_capability(
        "knowledge_search", permissions={"knowledge.read"}
    )
    assert resolution.selected_agent_id == "fallback_agent"
    assert resolution.fallback_available


def test_budget_cannot_exceed_system_maximum() -> None:
    requested = AgentExecutionBudget(max_inference_calls=9, max_output_chars=99999)
    maximum = AgentExecutionBudget(max_inference_calls=1, max_output_chars=1000)
    bounded = requested.bounded_by(maximum)
    assert bounded.max_inference_calls == 1
    assert bounded.max_output_chars == 1000


def test_plugin_allowlist_duplicate_compatibility_and_failure_isolation() -> None:
    catalog = build_core_capability_catalog()
    registry = AgentRegistry(catalog)
    plugins = PluginRegistry({"approved"})

    class Plugin:
        plugin = AgentPlugin(plugin_id="approved", version="1.0.0")

        def register(self, *_):
            raise RuntimeError("private")

    assert plugins.register_plugin(Plugin(), registry, catalog) is False
    assert plugins.failures == {"approved": "plugin_registration_failed"}
    with pytest.raises(AgentRegistrationError, match="Duplicate"):
        plugins.register_plugin(Plugin(), registry, catalog)


@pytest.mark.asyncio
async def test_runtime_execution_enforces_output_budget(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)

    class OutputAgent(HealthyAgent):
        async def execute(self, task, context):
            return AgentResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                status="success",
                structured_output={"source_count": 0, "facts": ["x" * 500]},
            )

    manager = manager_for(OutputAgent())
    await manager.initialize()
    budget = AgentExecutionBudget(
        max_inference_calls=0,
        max_retrieval_calls=1,
        max_output_chars=100,
    )
    plan = ExecutionPlan(
        objective="budget",
        required_agents=["test_agent"],
        tasks=[
            AgentTask(
                task_id="retrieve",
                agent_id="test_agent",
                capability="knowledge_search",
                objective="budget",
                output_contract="KnowledgeEvidenceV1",
                budget=budget,
            )
        ],
    )
    context = AgentExecutionContext(
        request_id="request",
        plan_id=plan.plan_id,
        task_id="plan",
        authenticated_user_snapshot=SimpleNamespace(id="user"),
        permissions=frozenset({"knowledge.read"}),
        department=None,
        role="employee",
        conversation_id=None,
        streaming=False,
        deadline=None,
        budget=budget,
        runtime_services=AgentRuntimeServices(
            database_adapter=None, knowledge_fetcher=lambda: None
        ),
    )
    results, _, _ = await ExecutionEngine(runtime_manager=manager).execute(
        plan, manager.registry, {"knowledge.read"}, context
    )
    assert results[0].error_category == "agent_budget_exceeded"
    assert manager.records["test_agent"].active_executions == 0

