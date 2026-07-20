from __future__ import annotations

from app.agents.capabilities import CapabilityCatalog, build_core_capability_catalog
from app.agents.errors import AgentRegistrationError
from app.agents.registry import AgentRegistry as RuntimeAgentRegistry
from app.agents.registry import EnterpriseAgent


AgentRegistryError = AgentRegistrationError


class AgentRegistry(RuntimeAgentRegistry):
    """Chapter 1-compatible registry backed by the Chapter 2 catalog."""

    def __init__(self, catalog: CapabilityCatalog | None = None) -> None:
        super().__init__(catalog or build_core_capability_catalog())


__all__ = ["AgentRegistry", "AgentRegistryError", "EnterpriseAgent"]
