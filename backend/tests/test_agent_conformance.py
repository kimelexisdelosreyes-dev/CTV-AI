from __future__ import annotations

import pytest

from app.agents.bootstrap import builtin_runtime_dependencies
from app.agents.capabilities import build_core_capability_catalog
from app.agents.plugins import PluginRegistry
from app.agents.runtime_manager import AgentRuntimeManager
from app.core.config import settings
from app.supervisor.agents import BuiltinCoreAgentPlugin
from app.supervisor.agent_registry import AgentRegistry
from tests.agents.conformance import AgentConformanceHarness


@pytest.mark.asyncio
async def test_all_five_core_agents_pass_conformance(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_agent_health_poll_enabled", False)
    catalog = build_core_capability_catalog()
    registry = AgentRegistry(catalog)
    plugin = BuiltinCoreAgentPlugin()
    plugin.register(registry, catalog)
    manager = AgentRuntimeManager(registry, catalog, PluginRegistry(set()))
    await manager.initialize(builtin_runtime_dependencies())
    harness = AgentConformanceHarness(manager)
    for agent_id in (
        "knowledge_agent",
        "operations_agent",
        "employee_agent",
        "reasoning_agent",
        "response_composer_agent",
    ):
        await harness.verify(agent_id)
    await harness.verify_shutdown_idempotent()

