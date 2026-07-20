from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agents.capabilities import CapabilityCatalog
from app.agents.errors import AgentRegistrationError
from app.agents.metrics import agent_runtime_metrics
from app.agents.models import AGENT_RUNTIME_CONTRACT_VERSION, SEMVER_PATTERN
from app.agents.registry import AgentRegistry, contract_compatible


class AgentPlugin(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    plugin_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: str
    required_runtime_contract: str = AGENT_RUNTIME_CONTRACT_VERSION
    enabled: bool = True

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("Plugin version must use semantic versioning.")
        return value


class RegistrablePlugin(Protocol):
    plugin: AgentPlugin

    def register(self, registry: AgentRegistry, catalog: CapabilityCatalog) -> None: ...


class PluginRegistry:
    def __init__(self, approved_plugin_ids: set[str]) -> None:
        self._approved = frozenset(approved_plugin_ids)
        self._plugins: dict[str, AgentPlugin] = {}
        self._failures: dict[str, str] = {}

    def register_plugin(
        self,
        implementation: RegistrablePlugin,
        registry: AgentRegistry,
        catalog: CapabilityCatalog,
    ) -> bool:
        plugin = implementation.plugin
        if plugin.plugin_id not in self._approved:
            raise AgentRegistrationError("Plugin is not in the internal allowlist.")
        if plugin.plugin_id in self._plugins:
            raise AgentRegistrationError(f"Duplicate plugin ID: {plugin.plugin_id}")
        if not contract_compatible(plugin.required_runtime_contract):
            raise AgentRegistrationError("Plugin runtime contract is incompatible.")
        if not plugin.enabled:
            self._plugins[plugin.plugin_id] = plugin
            return True
        self._plugins[plugin.plugin_id] = plugin
        try:
            implementation.register(registry, catalog)
        except Exception:
            self._failures[plugin.plugin_id] = "plugin_registration_failed"
            agent_runtime_metrics.increment("agent_plugin_registration_failure_count")
            return False
        return True

    def safe_diagnostics(self) -> list[dict[str, object]]:
        return [
            {
                "plugin_id": item.plugin_id,
                "version": item.version,
                "enabled": item.enabled,
                "registration_state": (
                    self._failures.get(item.plugin_id) or "registered"
                ),
            }
            for item in self._plugins.values()
        ]

    @property
    def failures(self) -> dict[str, str]:
        return dict(self._failures)
