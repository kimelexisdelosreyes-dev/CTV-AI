from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

from app.agents.models import AgentHealth, AgentLifecycleState, AgentReadiness


@dataclass
class AgentConformanceHarness:
    manager: object

    async def verify(self, agent_id: str) -> None:
        agent = self.manager.registry.get(agent_id)
        definition = agent.definition
        assert definition.agent_id == agent_id
        assert definition.capabilities
        assert definition.contract_version == "1.0"
        assert self.manager.state_for(agent_id) in {
            AgentLifecycleState.READY,
            AgentLifecycleState.DEGRADED,
        }
        health = await asyncio.wait_for(
            self.manager.health_check(agent_id), timeout=1.0
        )
        assert isinstance(health, AgentHealth)
        readiness = await self.manager.readiness_check(agent_id)
        assert isinstance(readiness, AgentReadiness)
        assert readiness.ready
        assert "exception" not in health.safe_message.lower()

    async def verify_shutdown_idempotent(self) -> None:
        await self.manager.shutdown()
        await self.manager.shutdown()

