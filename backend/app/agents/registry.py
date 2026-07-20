from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, Protocol

from app.agents.capabilities import CapabilityCatalog
from app.agents.errors import AgentRegistrationError
from app.agents.metrics import agent_runtime_metrics
from app.agents.models import (
    AGENT_RUNTIME_CONTRACT_VERSION,
    AgentDefinition,
    AgentLifecycleState,
    CapabilityResolution,
)


class EnterpriseAgent(Protocol):
    definition: AgentDefinition

    async def execute(self, task: Any, context: Any) -> Any: ...


def contract_compatible(candidate: str, runtime: str = AGENT_RUNTIME_CONTRACT_VERSION) -> bool:
    try:
        candidate_major, candidate_minor = (int(part) for part in candidate.split(".")[:2])
        runtime_major, runtime_minor = (int(part) for part in runtime.split(".")[:2])
    except (ValueError, TypeError):
        return False
    return candidate_major == runtime_major and candidate_minor <= runtime_minor


class AgentRegistry:
    def __init__(self, catalog: CapabilityCatalog) -> None:
        self.catalog = catalog
        self._agents: dict[str, EnterpriseAgent] = {}
        self._state_provider: Callable[[str], AgentLifecycleState] | None = None

    def set_state_provider(
        self, provider: Callable[[str], AgentLifecycleState] | None
    ) -> None:
        self._state_provider = provider

    def register(self, agent: EnterpriseAgent) -> None:
        definition = agent.definition
        if definition.agent_id in self._agents:
            raise AgentRegistrationError(f"Duplicate agent ID: {definition.agent_id}")
        if not definition.capabilities:
            raise AgentRegistrationError("Agents must declare at least one capability.")
        if not contract_compatible(definition.contract_version):
            raise AgentRegistrationError("Agent contract version is incompatible with runtime.")
        for capability_id in definition.capabilities:
            if capability_id not in self.catalog:
                raise AgentRegistrationError(f"Unknown capability: {capability_id}")
            capability = self.catalog.get(capability_id)
            if not capability.required_permissions.issubset(definition.required_permissions):
                raise AgentRegistrationError(
                    "Agent capability permissions may not be weaker than catalog permissions."
                )
            if definition.contract_version not in capability.compatible_agent_contract_versions:
                raise AgentRegistrationError("Capability contract version is incompatible.")
        self._agents[definition.agent_id] = agent

    def get(self, agent_id: str) -> EnterpriseAgent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise AgentRegistrationError(f"Unknown agent: {agent_id}") from exc

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
            if not enabled_only
            or (
                agent.definition.enabled
                and (
                    self._state_provider is None
                    or self._state_provider(agent.definition.agent_id)
                    in {AgentLifecycleState.READY, AgentLifecycleState.DEGRADED}
                )
            )
        ]

    def resolve_capability(
        self,
        capability_id: str,
        *,
        permissions: set[str],
        department: str | None = None,
        role: str | None = None,
        preferred_agent_id: str | None = None,
        disabled_capabilities: set[str] | None = None,
    ) -> CapabilityResolution:
        started = perf_counter()
        capability = self.catalog.get(capability_id)
        candidates: list[EnterpriseAgent] = []
        excluded: dict[str, str] = {}
        if capability_id in (disabled_capabilities or set()):
            return CapabilityResolution(
                capability_id=capability_id,
                excluded_candidates={},
                resolution_reason="capability_disabled",
                resolution_duration_ms=round((perf_counter() - started) * 1000, 3),
            )
        for agent in self.resolve(capability_id):
            definition = agent.definition
            reason = None
            state = (
                self._state_provider(definition.agent_id)
                if self._state_provider
                else AgentLifecycleState.READY
            )
            if state not in {AgentLifecycleState.READY, AgentLifecycleState.DEGRADED}:
                reason = f"lifecycle_{state.value}"
            elif not definition.required_permissions.issubset(permissions):
                reason = "permission_denied"
            elif not capability.required_permissions.issubset(permissions):
                reason = "capability_permission_denied"
            elif definition.output_schema != capability.output_schema:
                reason = "output_schema_incompatible"
            elif definition.department_allowlist and department not in definition.department_allowlist:
                reason = "department_not_allowed"
            elif definition.role_allowlist and role not in definition.role_allowlist:
                reason = "role_not_allowed"
            if reason:
                excluded[definition.agent_id] = reason
            else:
                candidates.append(agent)
        candidates.sort(
            key=lambda item: (
                item.definition.agent_id != preferred_agent_id,
                self._state_provider(item.definition.agent_id) == AgentLifecycleState.DEGRADED
                if self._state_provider
                else False,
                item.definition.priority,
                item.definition.agent_id,
            )
        )
        selected = candidates[0].definition.agent_id if candidates else None
        duration_ms = round((perf_counter() - started) * 1000, 3)
        metric = "capability_resolution_count" if selected else "capability_resolution_failure_count"
        agent_runtime_metrics.increment(metric, capability=capability_id)
        return CapabilityResolution(
            capability_id=capability_id,
            selected_agent_id=selected,
            candidate_agent_ids=[item.definition.agent_id for item in candidates],
            excluded_candidates=excluded,
            resolution_reason=(
                "preferred_agent_selected"
                if selected and selected == preferred_agent_id
                else "deterministic_priority"
                if selected
                else "no_eligible_agent"
            ),
            fallback_available=len(candidates) > 1,
            resolution_duration_ms=duration_ms,
        )

    def safe_diagnostics(self) -> list[dict[str, object]]:
        return [
            {
                "agent_id": item.agent_id,
                "display_name": item.display_name,
                "name": item.display_name,
                "capabilities": sorted(item.capabilities),
                "estimated_cost_class": item.estimated_cost_class,
                "supports_parallel_execution": item.supports_parallel_execution,
                "enabled": item.enabled,
                "version": item.version,
                "contract_version": item.contract_version,
            }
            for item in self.definitions()
        ]
