from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime
from time import perf_counter
from typing import Any

from app.agents.capabilities import CapabilityCatalog
from app.agents.errors import AgentErrorCategory, AgentRuntimeError
from app.agents.metrics import agent_runtime_metrics
from app.agents.models import (
    AGENT_RUNTIME_CONTRACT_VERSION,
    AgentHealth,
    AgentLifecycleState,
    AgentReadiness,
    AgentRuntimeContext,
    CapabilityResolution,
    RuntimeAgentRecord,
    utc_now,
)
from app.agents.plugins import PluginRegistry
from app.agents.registry import AgentRegistry
from app.core.config import settings


logger = logging.getLogger(__name__)


VALID_TRANSITIONS: dict[AgentLifecycleState, frozenset[AgentLifecycleState]] = {
    AgentLifecycleState.REGISTERED: frozenset(
        {AgentLifecycleState.INITIALIZING, AgentLifecycleState.DISABLED, AgentLifecycleState.STOPPED}
    ),
    AgentLifecycleState.INITIALIZING: frozenset(
        {AgentLifecycleState.READY, AgentLifecycleState.DEGRADED, AgentLifecycleState.UNAVAILABLE, AgentLifecycleState.FAILED}
    ),
    AgentLifecycleState.READY: frozenset(
        {AgentLifecycleState.DEGRADED, AgentLifecycleState.UNAVAILABLE, AgentLifecycleState.DRAINING, AgentLifecycleState.FAILED}
    ),
    AgentLifecycleState.DEGRADED: frozenset(
        {AgentLifecycleState.READY, AgentLifecycleState.UNAVAILABLE, AgentLifecycleState.DRAINING, AgentLifecycleState.FAILED}
    ),
    AgentLifecycleState.UNAVAILABLE: frozenset(
        {AgentLifecycleState.INITIALIZING, AgentLifecycleState.READY, AgentLifecycleState.DEGRADED, AgentLifecycleState.DRAINING, AgentLifecycleState.FAILED}
    ),
    AgentLifecycleState.DISABLED: frozenset({AgentLifecycleState.STOPPED}),
    AgentLifecycleState.DRAINING: frozenset({AgentLifecycleState.STOPPED, AgentLifecycleState.FAILED}),
    AgentLifecycleState.STOPPED: frozenset({AgentLifecycleState.INITIALIZING}),
    AgentLifecycleState.FAILED: frozenset({AgentLifecycleState.INITIALIZING, AgentLifecycleState.STOPPED}),
}


class AgentRuntimeManager:
    def __init__(
        self,
        registry: AgentRegistry,
        catalog: CapabilityCatalog,
        plugins: PluginRegistry,
    ) -> None:
        self.registry = registry
        self.catalog = catalog
        self.plugins = plugins
        self.records = {
            definition.agent_id: RuntimeAgentRecord(definition=definition)
            for definition in registry.definitions()
        }
        self.registry.set_state_provider(self.state_for)
        self.initialized_at: datetime | None = None
        self.last_health_poll_at: datetime | None = None
        self._health_stop = asyncio.Event()
        self._health_task: asyncio.Task[None] | None = None
        self._shutdown_complete = False
        self._dependencies: dict[Any, Any] = {}

    def state_for(self, agent_id: str) -> AgentLifecycleState:
        return self.records[agent_id].state

    def transition(self, agent_id: str, state: AgentLifecycleState) -> None:
        record = self.records[agent_id]
        if state == record.state:
            return
        if state not in VALID_TRANSITIONS[record.state]:
            raise ValueError(f"Invalid agent lifecycle transition: {record.state} -> {state}")
        record.state = state
        record.state_changed_at = utc_now()
        if state == AgentLifecycleState.DRAINING:
            record.draining_at = record.state_changed_at
        elif state == AgentLifecycleState.STOPPED:
            record.stopped_at = record.state_changed_at
        agent_runtime_metrics.gauge("agent_lifecycle_state", float(list(AgentLifecycleState).index(state)), agent_id=agent_id)

    async def initialize(self, dependencies: dict[Any, Any] | None = None) -> None:
        if self.initialized_at is not None:
            return
        self._dependencies = dict(dependencies or {})
        required_failures: list[str] = []
        if not settings.ctv_one_agent_runtime_enabled:
            for agent_id in self.records:
                self.transition(agent_id, AgentLifecycleState.DISABLED)
            self.initialized_at = utc_now()
            return
        for agent_id, record in self.records.items():
            if not self._enabled(record.definition):
                self.transition(agent_id, AgentLifecycleState.DISABLED)
                continue
            missing = record.definition.required_dependencies.difference(self._dependencies)
            if missing:
                self.transition(agent_id, AgentLifecycleState.INITIALIZING)
                self.transition(agent_id, AgentLifecycleState.UNAVAILABLE)
                record.safe_error_category = AgentErrorCategory.DEPENDENCY_UNAVAILABLE.value
                if record.definition.required:
                    required_failures.append(agent_id)
                continue
            self.transition(agent_id, AgentLifecycleState.INITIALIZING)
            started = perf_counter()
            try:
                hook = getattr(self.registry.get(agent_id), "initialize", None)
                if hook:
                    async with asyncio.timeout(settings.ctv_one_agent_initialize_timeout_seconds):
                        await hook(AgentRuntimeContext(dependencies=self._dependencies))
                record.initialized_at = utc_now()
                self.transition(agent_id, AgentLifecycleState.READY)
            except Exception:
                logger.exception("agent.initialize_failed agent_id=%s", agent_id)
                record.safe_error_category = AgentErrorCategory.INITIALIZATION_FAILED.value
                self.transition(agent_id, AgentLifecycleState.FAILED)
                if record.definition.required:
                    required_failures.append(agent_id)
            finally:
                duration = round((perf_counter() - started) * 1000, 3)
                agent_runtime_metrics.duration("agent_initialize_duration_ms", duration, agent_id=agent_id)
        self.initialized_at = utc_now()
        agent_runtime_metrics.gauge("agent_runtime_initialized", 1.0)
        if settings.ctv_one_agent_health_poll_enabled:
            self._health_stop.clear()
            self._health_task = asyncio.create_task(self._health_poll_loop())
        if required_failures:
            raise AgentRuntimeError(AgentErrorCategory.INITIALIZATION_FAILED)

    def _enabled(self, definition) -> bool:
        configured = {
            "knowledge_agent": settings.ctv_one_agent_knowledge_enabled,
            "operations_agent": settings.ctv_one_agent_operations_enabled,
            "employee_agent": settings.ctv_one_agent_employee_enabled,
            "reasoning_agent": settings.ctv_one_agent_reasoning_enabled,
            "response_composer_agent": settings.ctv_one_agent_composer_enabled,
        }.get(definition.agent_id, definition.enabled_by_default)
        return bool(definition.enabled_by_default and configured)

    async def health_check(self, agent_id: str) -> AgentHealth:
        record = self.records[agent_id]
        started = perf_counter()
        try:
            hook = getattr(self.registry.get(agent_id), "health_check", None)
            if hook:
                async with asyncio.timeout(settings.ctv_one_agent_health_timeout_seconds):
                    health = AgentHealth.model_validate(await hook())
            else:
                health = AgentHealth(status="healthy")
            record.consecutive_health_failures = 0
            record.consecutive_health_successes += 1
            health.consecutive_failures = 0
            health.last_success_at = utc_now()
            if (
                record.state in {AgentLifecycleState.DEGRADED, AgentLifecycleState.UNAVAILABLE}
                and record.consecutive_health_successes
                >= settings.ctv_one_agent_recovery_success_threshold
            ):
                self.transition(agent_id, AgentLifecycleState.READY)
        except Exception:
            logger.exception("agent.health_failed agent_id=%s", agent_id)
            record.consecutive_health_failures += 1
            record.consecutive_health_successes = 0
            threshold = settings.ctv_one_agent_failure_threshold
            health = AgentHealth(
                status=("unavailable" if record.consecutive_health_failures >= threshold else "degraded"),
                safe_message="Agent health check failed safely.",
                consecutive_failures=record.consecutive_health_failures,
                last_failure_at=utc_now(),
            )
            target = (
                AgentLifecycleState.UNAVAILABLE
                if record.consecutive_health_failures >= threshold
                else AgentLifecycleState.DEGRADED
            )
            if record.state != target:
                self.transition(agent_id, target)
        health.duration_ms = round((perf_counter() - started) * 1000, 3)
        record.last_health = health
        agent_runtime_metrics.duration("agent_health_check_duration_ms", health.duration_ms, agent_id=agent_id)
        return health

    async def readiness_check(self, agent_id: str) -> AgentReadiness:
        record = self.records[agent_id]
        ready = record.state in {AgentLifecycleState.READY, AgentLifecycleState.DEGRADED}
        hook = getattr(self.registry.get(agent_id), "readiness_check", None)
        if ready and hook:
            result = AgentReadiness.model_validate(await hook())
            ready = result.ready
        return AgentReadiness(
            ready=ready,
            reason_category=None if ready else f"agent_{record.state.value}",
            capability_availability={capability: ready for capability in record.definition.capabilities},
        )

    async def _health_poll_loop(self) -> None:
        try:
            while not self._health_stop.is_set():
                try:
                    await asyncio.wait_for(
                        self._health_stop.wait(),
                        timeout=settings.ctv_one_agent_health_poll_seconds,
                    )
                    break
                except TimeoutError:
                    pass
                self.last_health_poll_at = utc_now()
                await asyncio.gather(
                    *(
                        self.health_check(agent_id)
                        for agent_id, record in self.records.items()
                        if record.state in {
                            AgentLifecycleState.READY,
                            AgentLifecycleState.DEGRADED,
                            AgentLifecycleState.UNAVAILABLE,
                        }
                    ),
                    return_exceptions=True,
                )
        except asyncio.CancelledError:
            raise

    def resolve_capability(self, capability_id: str, **kwargs: Any) -> CapabilityResolution:
        kwargs.setdefault(
            "disabled_capabilities",
            {
                item.strip()
                for item in settings.ctv_one_agent_disabled_capabilities.split(",")
                if item.strip()
            },
        )
        return self.registry.resolve_capability(capability_id, **kwargs)

    async def begin_execution(self, agent_id: str) -> None:
        state = self.state_for(agent_id)
        categories = {
            AgentLifecycleState.DISABLED: AgentErrorCategory.DISABLED,
            AgentLifecycleState.DRAINING: AgentErrorCategory.NOT_READY,
            AgentLifecycleState.UNAVAILABLE: AgentErrorCategory.UNAVAILABLE,
        }
        if state not in {AgentLifecycleState.READY, AgentLifecycleState.DEGRADED}:
            raise AgentRuntimeError(categories.get(state, AgentErrorCategory.NOT_READY))
        self.records[agent_id].active_executions += 1

    def end_execution(self, agent_id: str) -> None:
        record = self.records[agent_id]
        record.active_executions = max(record.active_executions - 1, 0)

    async def drain(self) -> None:
        for agent_id, record in self.records.items():
            if record.state in {AgentLifecycleState.READY, AgentLifecycleState.DEGRADED, AgentLifecycleState.UNAVAILABLE}:
                self.transition(agent_id, AgentLifecycleState.DRAINING)
                hook = getattr(self.registry.get(agent_id), "drain", None)
                if hook:
                    await hook()

    async def shutdown(self) -> None:
        if self._shutdown_complete:
            return
        self._health_stop.set()
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        await self.drain()
        for agent_id, record in self.records.items():
            if record.state == AgentLifecycleState.DISABLED:
                self.transition(agent_id, AgentLifecycleState.STOPPED)
                continue
            if record.state != AgentLifecycleState.DRAINING:
                continue
            try:
                hook = getattr(self.registry.get(agent_id), "shutdown", None)
                if hook:
                    async with asyncio.timeout(settings.ctv_one_agent_shutdown_timeout_seconds):
                        await hook()
                self.transition(agent_id, AgentLifecycleState.STOPPED)
            except Exception:
                logger.exception("agent.shutdown_failed agent_id=%s", agent_id)
                self.transition(agent_id, AgentLifecycleState.FAILED)
        self._shutdown_complete = True

    async def status(self) -> dict[str, object]:
        counts = Counter(record.state.value for record in self.records.values())
        agents = []
        for agent_id, record in self.records.items():
            readiness = await self.readiness_check(agent_id)
            agents.append(
                {
                    "agent_id": agent_id,
                    "display_name": record.definition.display_name,
                    "version": record.definition.version,
                    "contract_version": record.definition.contract_version,
                    "lifecycle_state": record.state.value,
                    "readiness": readiness.model_dump(mode="json"),
                    "capabilities": sorted(record.definition.capabilities),
                    "department_allowlist": sorted(record.definition.department_allowlist),
                    "role_allowlist": sorted(record.definition.role_allowlist),
                    "consecutive_health_failures": record.consecutive_health_failures,
                    "last_health_check_at": (
                        record.last_health.checked_at.isoformat() if record.last_health else None
                    ),
                    "safe_dependency_states": {
                        dependency.value: (
                            "available" if dependency in self._dependencies else "unavailable"
                        )
                        for dependency in record.definition.required_dependencies
                        | record.definition.optional_dependencies
                    },
                }
            )
        available_capabilities = {
            capability
            for record in self.records.values()
            if record.state in {AgentLifecycleState.READY, AgentLifecycleState.DEGRADED}
            for capability in record.definition.capabilities
        }
        return {
            "runtime_enabled": settings.ctv_one_agent_runtime_enabled,
            "runtime_contract_version": AGENT_RUNTIME_CONTRACT_VERSION,
            "initialized_at": self.initialized_at.isoformat() if self.initialized_at else None,
            "total_agents": len(self.records),
            "ready_agents": counts[AgentLifecycleState.READY.value],
            "degraded_agents": counts[AgentLifecycleState.DEGRADED.value],
            "unavailable_agents": counts[AgentLifecycleState.UNAVAILABLE.value],
            "disabled_agents": counts[AgentLifecycleState.DISABLED.value],
            "draining_agents": counts[AgentLifecycleState.DRAINING.value],
            "capability_count": len(self.catalog.definitions()),
            "available_capability_count": len(available_capabilities),
            "lifecycle_counts": dict(counts),
            "health_poll_enabled": settings.ctv_one_agent_health_poll_enabled,
            "last_health_poll_at": self.last_health_poll_at.isoformat() if self.last_health_poll_at else None,
            "registered_plugins": self.plugins.safe_diagnostics(),
            "agents": agents,
            "configuration_limits": {
                "health_timeout_seconds": settings.ctv_one_agent_health_timeout_seconds,
                "initialize_timeout_seconds": settings.ctv_one_agent_initialize_timeout_seconds,
                "shutdown_timeout_seconds": settings.ctv_one_agent_shutdown_timeout_seconds,
                "failure_threshold": settings.ctv_one_agent_failure_threshold,
                "recovery_success_threshold": settings.ctv_one_agent_recovery_success_threshold,
                "max_inference_calls": settings.ctv_one_agent_default_max_inference_calls,
                "max_retrieval_calls": settings.ctv_one_agent_default_max_retrieval_calls,
                "max_evidence_items": settings.ctv_one_agent_default_max_evidence_items,
                "max_output_chars": settings.ctv_one_agent_default_max_output_chars,
                "max_queue_wait_seconds": settings.ctv_one_agent_default_max_queue_wait_seconds,
                "reasoning_timeout_seconds": settings.ctv_one_agent_reasoning_timeout_seconds,
                "composer_timeout_seconds": settings.ctv_one_agent_composer_timeout_seconds,
                "composition_max_evidence_items": settings.ctv_one_agent_composition_max_evidence_items,
                "composition_max_chars_per_result": settings.ctv_one_agent_composition_max_chars_per_result,
                "composition_max_total_chars": settings.ctv_one_agent_composition_max_total_chars,
            },
            "metrics": agent_runtime_metrics.safe_snapshot(),
        }
