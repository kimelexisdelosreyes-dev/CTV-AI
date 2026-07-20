from __future__ import annotations

from typing import Protocol

from app.supervisor.schemas import AgentDefinition, AgentResult, AgentTask


class EnterpriseAgent(Protocol):
    definition: AgentDefinition

    async def execute(self, task: AgentTask, context) -> AgentResult: ...


class AgentRegistryError(ValueError):
    pass


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, EnterpriseAgent] = {}

    def register(self, agent: EnterpriseAgent) -> None:
        definition = agent.definition
        if definition.agent_id in self._agents:
            raise AgentRegistryError(f"Duplicate agent ID: {definition.agent_id}")
        if not definition.capabilities:
            raise AgentRegistryError("Agents must declare at least one capability.")
        if any(not capability.replace("_", "").isalnum() for capability in definition.capabilities):
            raise AgentRegistryError("Agent capability declarations are invalid.")
        self._agents[definition.agent_id] = agent

    def get(self, agent_id: str) -> EnterpriseAgent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise AgentRegistryError(f"Unknown agent: {agent_id}") from exc

    def resolve(self, capability: str) -> list[EnterpriseAgent]:
        return [
            agent
            for agent in self._agents.values()
            if agent.definition.enabled and capability in agent.definition.capabilities
        ]

    def definitions(self, *, enabled_only: bool = False) -> list[AgentDefinition]:
        return [
            agent.definition
            for agent in self._agents.values()
            if not enabled_only or agent.definition.enabled
        ]

    def safe_diagnostics(self) -> list[dict[str, object]]:
        return [
            {
                "agent_id": item.agent_id,
                "name": item.name,
                "capabilities": sorted(item.capabilities),
                "estimated_cost_class": item.estimated_cost_class,
                "supports_parallel_execution": item.supports_parallel_execution,
                "enabled": item.enabled,
                "version": item.version,
            }
            for item in self.definitions()
        ]
