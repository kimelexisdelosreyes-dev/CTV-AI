from __future__ import annotations

import asyncio
import logging
from collections import Counter
from time import perf_counter
from typing import Mapping

from app.atlas.constants import (
    ATLAS_CONTEXT_PACKAGE_VERSION,
    ATLAS_PROVIDER_CONTRACT_VERSION,
    ATLAS_RUNTIME_VERSION,
)
from app.atlas.diagnostics import safe_provider_diagnostic
from app.atlas.errors import AtlasErrorCategory
from app.atlas.health import failed_health
from app.atlas.lifecycle import transition_record
from app.atlas.metrics import AtlasRuntimeMetrics, atlas_runtime_metrics
from app.atlas.models import (
    AtlasHealthStatus,
    AtlasProviderHealth,
    AtlasProviderLifecycleState,
    AtlasProviderReadiness,
    AtlasProviderRuntimeRecord,
    AtlasRuntimeConfigurationSnapshot,
    AtlasRuntimeState,
    utc_now,
)
from app.atlas.provider import AtlasRuntimeContext
from app.atlas.readiness import state_readiness
from app.atlas.registry import AtlasProviderRegistry
from app.core.config import settings


logger = logging.getLogger(__name__)


class AtlasRuntimeManager:
    """Owns the idle Atlas provider runtime outside every request path."""

    def __init__(
        self,
        registry: AtlasProviderRegistry,
        *,
        metrics: AtlasRuntimeMetrics = atlas_runtime_metrics,
    ) -> None:
        self.registry = registry
        self.metrics = metrics
        self.records = self._new_records()
        self.runtime_state = AtlasRuntimeState.CREATED
        self.initialized_at = None
        self.stopped_at = None
        self.last_health_poll_at = None
        self.required_provider_failures: list[str] = []
        self._dependency_adapters: dict[str, object] = {}
        self._health_stop = asyncio.Event()
        self._health_task: asyncio.Task[None] | None = None
        self._shutdown_complete = False
        self._initialize_lock = asyncio.Lock()

    def _new_records(self) -> dict[str, AtlasProviderRuntimeRecord]:
        return {
            definition.provider_id: AtlasProviderRuntimeRecord(definition=definition)
            for definition in self.registry.definitions()
        }

    def _configuration_snapshot(self) -> AtlasRuntimeConfigurationSnapshot:
        return AtlasRuntimeConfigurationSnapshot(
            health_timeout_seconds=settings.ctv_one_atlas_health_timeout_seconds,
            initialize_timeout_seconds=settings.ctv_one_atlas_initialize_timeout_seconds,
            shutdown_timeout_seconds=settings.ctv_one_atlas_shutdown_timeout_seconds,
            failure_threshold=settings.ctv_one_atlas_failure_threshold,
            recovery_threshold=settings.ctv_one_atlas_recovery_threshold,
        )

    def _set_runtime_state(self, state: AtlasRuntimeState) -> None:
        self.runtime_state = state
        self.metrics.gauge(
            "atlas_runtime_state",
            float(list(AtlasRuntimeState).index(state)),
            lifecycle_state=state.value,
        )

    def _record_state_metric(self, provider_id: str) -> None:
        state = self.records[provider_id].state
        self.metrics.gauge(
            "atlas_provider_lifecycle_state",
            float(list(AtlasProviderLifecycleState).index(state)),
            provider_id=provider_id,
            lifecycle_state=state.value,
        )

    def transition(self, provider_id: str, target: AtlasProviderLifecycleState) -> None:
        transition_record(self.records[provider_id], target)
        self._record_state_metric(provider_id)

    async def initialize(self, dependency_adapters: Mapping[str, object] | None = None) -> None:
        """Initialize exactly once per active lifespan; a stopped runtime supports controlled restart."""
        async with self._initialize_lock:
            if self.runtime_state in {
                AtlasRuntimeState.INITIALIZING,
                AtlasRuntimeState.READY,
                AtlasRuntimeState.DEGRADED,
            }:
                return
            if self.runtime_state == AtlasRuntimeState.STOPPED:
                # Explicit controlled restart policy: reconstruct terminal provider records
                # from the immutable, already-approved registry definitions.
                self.records = self._new_records()
                self._shutdown_complete = False
                self.required_provider_failures = []
            self.registry.begin_runtime_initialization()
            self._dependency_adapters = dict(dependency_adapters or {})
            self._set_runtime_state(AtlasRuntimeState.INITIALIZING)
            self.metrics.increment("atlas_runtime_initialize_count")
            if not settings.ctv_one_atlas_enabled:
                for provider_id in self.records:
                    self.transition(provider_id, AtlasProviderLifecycleState.DISABLED)
                self.initialized_at = utc_now()
                self._set_runtime_state(AtlasRuntimeState.STOPPED)
                return

            context = AtlasRuntimeContext.create(
                configuration=self._configuration_snapshot(),
                safe_logger=logger,
                metrics=self.metrics,
                cancellation_signal=self._health_stop,
                dependency_adapters=self._dependency_adapters,
            )
            required_failures: list[str] = []
            for provider_id, provider in self.registry.providers():
                record = self.records[provider_id]
                if not record.definition.enabled_by_default:
                    self.transition(provider_id, AtlasProviderLifecycleState.DISABLED)
                    continue
                missing = record.definition.required_dependencies.difference(self._dependency_adapters)
                if missing:
                    self.transition(provider_id, AtlasProviderLifecycleState.INITIALIZING)
                    self.transition(provider_id, AtlasProviderLifecycleState.UNAVAILABLE)
                    record.failure_reason_category = AtlasErrorCategory.PROVIDER_DEPENDENCY_UNAVAILABLE.value
                    if record.definition.required:
                        required_failures.append(provider_id)
                    continue
                self.transition(provider_id, AtlasProviderLifecycleState.INITIALIZING)
                started = perf_counter()
                try:
                    async with asyncio.timeout(settings.ctv_one_atlas_initialize_timeout_seconds):
                        await provider.initialize(context)
                    record.initialized_at = utc_now()
                    self.transition(provider_id, AtlasProviderLifecycleState.READY)
                    self.metrics.increment("atlas_provider_initialize_count", provider_id=provider_id)
                    await self.readiness_check(provider_id)
                    if (
                        record.definition.required
                        and record.state != AtlasProviderLifecycleState.READY
                    ):
                        required_failures.append(provider_id)
                except TimeoutError:
                    logger.warning("atlas.provider_initialize_timeout provider_id=%s", provider_id)
                    record.failure_reason_category = AtlasErrorCategory.PROVIDER_TIMEOUT.value
                    self.transition(provider_id, AtlasProviderLifecycleState.FAILED)
                    self.metrics.increment(
                        "atlas_provider_initialize_failure_count",
                        provider_id=provider_id,
                        reason_category=AtlasErrorCategory.PROVIDER_TIMEOUT.value,
                    )
                    if record.definition.required:
                        required_failures.append(provider_id)
                except Exception:
                    logger.exception("atlas.provider_initialize_failed provider_id=%s", provider_id)
                    record.failure_reason_category = AtlasErrorCategory.PROVIDER_INITIALIZATION_FAILED.value
                    self.transition(provider_id, AtlasProviderLifecycleState.FAILED)
                    self.metrics.increment(
                        "atlas_provider_initialize_failure_count",
                        provider_id=provider_id,
                        reason_category=AtlasErrorCategory.PROVIDER_INITIALIZATION_FAILED.value,
                    )
                    if record.definition.required:
                        required_failures.append(provider_id)
                finally:
                    self.metrics.duration(
                        "atlas_provider_initialize_duration_ms",
                        (perf_counter() - started) * 1000,
                        provider_id=provider_id,
                    )
            self.initialized_at = utc_now()
            self.required_provider_failures = sorted(required_failures)
            self._set_runtime_state(
                AtlasRuntimeState.DEGRADED if required_failures else AtlasRuntimeState.READY
            )
            if settings.ctv_one_atlas_health_poll_enabled and self.records:
                self._health_stop.clear()
                self._health_task = asyncio.create_task(self._health_poll_loop())

    async def health_check(self, provider_id: str) -> AtlasProviderHealth:
        record = self.records[provider_id]
        if record.state in {AtlasProviderLifecycleState.DISABLED, AtlasProviderLifecycleState.STOPPED}:
            health = AtlasProviderHealth(
                status=AtlasHealthStatus.DISABLED,
                safe_message="Atlas provider is not eligible for health polling.",
            )
            record.last_health = health
            return health
        if record.state not in {
            AtlasProviderLifecycleState.READY,
            AtlasProviderLifecycleState.DEGRADED,
            AtlasProviderLifecycleState.UNAVAILABLE,
        }:
            return failed_health(unavailable=True, consecutive_failures=record.consecutive_health_failures)
        started = perf_counter()
        timeout = False
        try:
            provider = self.registry.get(provider_id)
            async with asyncio.timeout(settings.ctv_one_atlas_health_timeout_seconds):
                health = AtlasProviderHealth.model_validate(await provider.health_check())
            if health.status == AtlasHealthStatus.HEALTHY:
                record.consecutive_health_failures = 0
                record.consecutive_health_successes += 1
                health = health.model_copy(
                    update={
                        "consecutive_failures": 0,
                        "last_success_at": utc_now(),
                    }
                )
                if (
                    record.state
                    in {AtlasProviderLifecycleState.DEGRADED, AtlasProviderLifecycleState.UNAVAILABLE}
                    and record.consecutive_health_successes >= settings.ctv_one_atlas_recovery_threshold
                ):
                    self.transition(provider_id, AtlasProviderLifecycleState.READY)
            else:
                health = self._record_health_failure(provider_id)
        except TimeoutError:
            timeout = True
            logger.warning("atlas.provider_health_timeout provider_id=%s", provider_id)
            health = self._record_health_failure(provider_id, timeout=True)
        except Exception:
            logger.exception("atlas.provider_health_failed provider_id=%s", provider_id)
            health = self._record_health_failure(provider_id)
        duration = (perf_counter() - started) * 1000
        health = health.model_copy(update={"duration_ms": round(duration, 3)})
        record.last_health = health
        self.metrics.increment("atlas_provider_health_check_count", provider_id=provider_id)
        if health.status != AtlasHealthStatus.HEALTHY:
            self.metrics.increment(
                "atlas_provider_health_check_failure_count",
                provider_id=provider_id,
                reason_category=(
                    AtlasErrorCategory.PROVIDER_TIMEOUT.value
                    if timeout
                    else AtlasErrorCategory.PROVIDER_HEALTH_FAILED.value
                ),
            )
        self.metrics.duration("atlas_provider_health_check_duration_ms", duration, provider_id=provider_id)
        self.metrics.gauge(
            "atlas_provider_readiness",
            1.0 if record.state in {AtlasProviderLifecycleState.READY, AtlasProviderLifecycleState.DEGRADED} else 0.0,
            provider_id=provider_id,
            lifecycle_state=record.state.value,
            health_status=health.status.value,
        )
        self._refresh_required_runtime_state()
        return health

    def _record_health_failure(self, provider_id: str, *, timeout: bool = False) -> AtlasProviderHealth:
        record = self.records[provider_id]
        record.consecutive_health_failures += 1
        record.consecutive_health_successes = 0
        record.failure_reason_category = (
            AtlasErrorCategory.PROVIDER_TIMEOUT.value
            if timeout
            else AtlasErrorCategory.PROVIDER_HEALTH_FAILED.value
        )
        unavailable = record.consecutive_health_failures >= settings.ctv_one_atlas_failure_threshold
        target = (
            AtlasProviderLifecycleState.UNAVAILABLE
            if unavailable
            else AtlasProviderLifecycleState.DEGRADED
        )
        if record.state != target:
            self.transition(provider_id, target)
        self._refresh_required_runtime_state()
        return failed_health(
            unavailable=unavailable,
            consecutive_failures=record.consecutive_health_failures,
            timeout=timeout,
        )

    def _refresh_required_runtime_state(self) -> None:
        failed = sorted(
            provider_id
            for provider_id, record in self.records.items()
            if record.definition.required
            and record.state
            in {AtlasProviderLifecycleState.DEGRADED, AtlasProviderLifecycleState.UNAVAILABLE, AtlasProviderLifecycleState.FAILED}
        )
        self.required_provider_failures = failed
        if self.runtime_state not in {AtlasRuntimeState.INITIALIZING, AtlasRuntimeState.STOPPING, AtlasRuntimeState.STOPPED}:
            self._set_runtime_state(AtlasRuntimeState.DEGRADED if failed else AtlasRuntimeState.READY)

    async def readiness_check(self, provider_id: str) -> AtlasProviderReadiness:
        record = self.records[provider_id]
        state_value = state_readiness(record)
        if not state_value.ready:
            record.last_readiness = state_value
            return state_value
        started = perf_counter()
        try:
            provider = self.registry.get(provider_id)
            async with asyncio.timeout(settings.ctv_one_atlas_health_timeout_seconds):
                readiness = AtlasProviderReadiness.model_validate(await provider.readiness_check())
            if not readiness.ready and record.state == AtlasProviderLifecycleState.READY:
                record.failure_reason_category = AtlasErrorCategory.PROVIDER_READINESS_FAILED.value
                self.transition(provider_id, AtlasProviderLifecycleState.DEGRADED)
        except TimeoutError:
            logger.warning("atlas.provider_readiness_timeout provider_id=%s", provider_id)
            record.failure_reason_category = AtlasErrorCategory.PROVIDER_TIMEOUT.value
            if record.state == AtlasProviderLifecycleState.READY:
                self.transition(provider_id, AtlasProviderLifecycleState.DEGRADED)
            readiness = AtlasProviderReadiness(
                ready=False,
                reason_category=AtlasErrorCategory.PROVIDER_TIMEOUT.value,
                unavailable_capabilities=record.definition.capabilities,
            )
        except Exception:
            logger.exception("atlas.provider_readiness_failed provider_id=%s", provider_id)
            record.failure_reason_category = AtlasErrorCategory.PROVIDER_READINESS_FAILED.value
            if record.state == AtlasProviderLifecycleState.READY:
                self.transition(provider_id, AtlasProviderLifecycleState.DEGRADED)
            readiness = AtlasProviderReadiness(
                ready=False,
                reason_category=AtlasErrorCategory.PROVIDER_READINESS_FAILED.value,
                unavailable_capabilities=record.definition.capabilities,
            )
        self.metrics.duration(
            "atlas_provider_health_check_duration_ms",
            (perf_counter() - started) * 1000,
            provider_id=provider_id,
        )
        record.last_readiness = readiness
        self._refresh_required_runtime_state()
        return readiness

    async def _health_poll_loop(self) -> None:
        try:
            while not self._health_stop.is_set():
                try:
                    await asyncio.wait_for(
                        self._health_stop.wait(),
                        timeout=settings.ctv_one_atlas_health_poll_seconds,
                    )
                    break
                except TimeoutError:
                    pass
                self.last_health_poll_at = utc_now()
                eligible = [
                    provider_id
                    for provider_id, record in self.records.items()
                    if record.state
                    in {
                        AtlasProviderLifecycleState.READY,
                        AtlasProviderLifecycleState.DEGRADED,
                        AtlasProviderLifecycleState.UNAVAILABLE,
                    }
                ]
                await asyncio.gather(*(self.health_check(provider_id) for provider_id in eligible))
                await asyncio.gather(*(self.readiness_check(provider_id) for provider_id in eligible))
        except asyncio.CancelledError:
            raise

    async def drain(self) -> None:
        for provider_id, provider in self.registry.providers():
            record = self.records[provider_id]
            if record.state not in {
                AtlasProviderLifecycleState.READY,
                AtlasProviderLifecycleState.DEGRADED,
                AtlasProviderLifecycleState.UNAVAILABLE,
            }:
                continue
            self.transition(provider_id, AtlasProviderLifecycleState.DRAINING)
            try:
                async with asyncio.timeout(settings.ctv_one_atlas_shutdown_timeout_seconds):
                    await provider.drain()
            except TimeoutError:
                logger.warning("atlas.provider_drain_timeout provider_id=%s", provider_id)
                record.failure_reason_category = AtlasErrorCategory.PROVIDER_TIMEOUT.value
            except Exception:
                logger.exception("atlas.provider_drain_failed provider_id=%s", provider_id)
                record.failure_reason_category = AtlasErrorCategory.PROVIDER_SHUTDOWN_FAILED.value

    async def shutdown(self) -> None:
        if self._shutdown_complete:
            return
        self._set_runtime_state(AtlasRuntimeState.STOPPING)
        self._health_stop.set()
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None
        await self.drain()
        for provider_id, provider in self.registry.providers():
            record = self.records[provider_id]
            if record.state == AtlasProviderLifecycleState.DISABLED:
                self.transition(provider_id, AtlasProviderLifecycleState.STOPPED)
                continue
            if record.state == AtlasProviderLifecycleState.FAILED:
                self.transition(provider_id, AtlasProviderLifecycleState.STOPPED)
                continue
            if record.state != AtlasProviderLifecycleState.DRAINING:
                continue
            started = perf_counter()
            try:
                async with asyncio.timeout(settings.ctv_one_atlas_shutdown_timeout_seconds):
                    await provider.shutdown()
                self.transition(provider_id, AtlasProviderLifecycleState.STOPPED)
                self.metrics.increment("atlas_provider_shutdown_count", provider_id=provider_id)
            except TimeoutError:
                logger.warning("atlas.provider_shutdown_timeout provider_id=%s", provider_id)
                record.failure_reason_category = AtlasErrorCategory.PROVIDER_TIMEOUT.value
                self.transition(provider_id, AtlasProviderLifecycleState.STOPPED)
            except Exception:
                logger.exception("atlas.provider_shutdown_failed provider_id=%s", provider_id)
                record.failure_reason_category = AtlasErrorCategory.PROVIDER_SHUTDOWN_FAILED.value
                self.transition(provider_id, AtlasProviderLifecycleState.STOPPED)
            finally:
                self.metrics.duration(
                    "atlas_provider_shutdown_duration_ms",
                    (perf_counter() - started) * 1000,
                    provider_id=provider_id,
                )
        self.stopped_at = utc_now()
        self._shutdown_complete = True
        self.metrics.increment("atlas_runtime_shutdown_count")
        self._set_runtime_state(AtlasRuntimeState.STOPPED)

    async def status(self) -> dict[str, object]:
        """Return cached lifecycle/readiness state; diagnostics run no provider hooks."""
        counts = Counter(record.state.value for record in self.records.values())
        providers = []
        for provider_id, record in self.records.items():
            readiness = record.last_readiness or state_readiness(record)
            providers.append(
                safe_provider_diagnostic(
                    {
                        "provider_id": provider_id,
                        "display_name": record.definition.display_name,
                        "version": record.definition.version,
                        "contract_version": record.definition.contract_version,
                        "lifecycle_state": record.state.value,
                        "readiness": readiness.model_dump(mode="json"),
                        "capabilities": sorted(record.definition.capabilities),
                        "required": record.definition.required,
                        "enabled": record.definition.enabled_by_default,
                        "consecutive_health_failures": record.consecutive_health_failures,
                        "consecutive_health_successes": record.consecutive_health_successes,
                        "last_health_check_at": (
                            record.last_health.checked_at.isoformat() if record.last_health else None
                        ),
                        "safe_dependency_states": {
                            dependency: (
                                "available" if dependency in self._dependency_adapters else "unavailable"
                            )
                            for dependency in sorted(
                                record.definition.required_dependencies
                                | record.definition.optional_dependencies
                            )
                        },
                    }
                )
            )
        return {
            "atlas_enabled": settings.ctv_one_atlas_enabled,
            "runtime_state": self.runtime_state.value,
            "runtime_ready": self.runtime_state == AtlasRuntimeState.READY,
            "runtime_version": ATLAS_RUNTIME_VERSION,
            "provider_contract_version": ATLAS_PROVIDER_CONTRACT_VERSION,
            "context_package_version": ATLAS_CONTEXT_PACKAGE_VERSION,
            "initialized_at": self.initialized_at.isoformat() if self.initialized_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "registered_provider_count": len(self.records),
            "ready_provider_count": counts[AtlasProviderLifecycleState.READY.value],
            "degraded_provider_count": counts[AtlasProviderLifecycleState.DEGRADED.value],
            "unavailable_provider_count": counts[AtlasProviderLifecycleState.UNAVAILABLE.value],
            "disabled_provider_count": counts[AtlasProviderLifecycleState.DISABLED.value],
            "failed_provider_count": counts[AtlasProviderLifecycleState.FAILED.value],
            "lifecycle_counts": dict(counts),
            "health_poll_enabled": settings.ctv_one_atlas_health_poll_enabled,
            "health_poll_interval_seconds": settings.ctv_one_atlas_health_poll_seconds,
            "last_health_poll_at": self.last_health_poll_at.isoformat() if self.last_health_poll_at else None,
            "required_provider_failures": list(self.required_provider_failures),
            "configuration_limits": {
                "health_timeout_seconds": settings.ctv_one_atlas_health_timeout_seconds,
                "initialize_timeout_seconds": settings.ctv_one_atlas_initialize_timeout_seconds,
                "shutdown_timeout_seconds": settings.ctv_one_atlas_shutdown_timeout_seconds,
                "failure_threshold": settings.ctv_one_atlas_failure_threshold,
                "recovery_threshold": settings.ctv_one_atlas_recovery_threshold,
            },
            "providers": providers,
            "metrics": self.metrics.safe_snapshot(),
        }
