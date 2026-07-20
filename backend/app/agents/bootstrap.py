from __future__ import annotations

from app.agents.capabilities import build_core_capability_catalog
from app.agents.models import DependencyIdentifier
from app.agents.plugins import PluginRegistry
from app.agents.registry import AgentRegistry
from app.agents.runtime_manager import AgentRuntimeManager
from app.services.context_engine import context_engine
from app.services.inference_queue import inference_queue
from app.services.ollama_service import ollama_service
from app.services.operations_context_service import operations_context_service
from app.supervisor.agents import BuiltinCoreAgentPlugin


capability_catalog = build_core_capability_catalog()
agent_registry = AgentRegistry(capability_catalog)
plugin_registry = PluginRegistry({"ctv_one_core_agents"})
plugin_registry.register_plugin(
    BuiltinCoreAgentPlugin(), agent_registry, capability_catalog
)
agent_runtime_manager = AgentRuntimeManager(
    agent_registry, capability_catalog, plugin_registry
)


def builtin_runtime_dependencies() -> dict[DependencyIdentifier, object]:
    """Static, application-approved service map; never populated from requests."""
    return {
        DependencyIdentifier.KNOWLEDGE_SERVICE: object(),
        DependencyIdentifier.OPERATIONS_SNAPSHOT_SERVICE: operations_context_service,
        DependencyIdentifier.EMPLOYEE_INTELLIGENCE_SERVICE: context_engine,
        DependencyIdentifier.INFERENCE_QUEUE: inference_queue,
        DependencyIdentifier.OLLAMA_CLIENT: ollama_service,
        DependencyIdentifier.DATABASE_ADAPTER: object(),
    }

