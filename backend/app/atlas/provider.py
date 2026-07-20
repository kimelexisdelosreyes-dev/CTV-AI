from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import Logger
from types import MappingProxyType
from typing import Mapping

from app.atlas.constants import ATLAS_PROVIDER_CONTRACT_VERSION, ATLAS_RUNTIME_VERSION
from app.atlas.metrics import AtlasRuntimeMetrics
from app.atlas.models import (
    AtlasProviderCollectionContext,
    AtlasProviderDefinition,
    AtlasProviderHealth,
    AtlasProviderReadiness,
    AtlasProviderRequest,
    AtlasProviderResult,
    AtlasRuntimeConfigurationSnapshot,
)


@dataclass(frozen=True)
class AtlasRuntimeContext:
    """Narrow, server-constructed context exposed to approved providers only."""

    configuration: AtlasRuntimeConfigurationSnapshot
    safe_logger: Logger
    metrics: AtlasRuntimeMetrics
    cancellation_signal: object
    dependency_adapters: Mapping[str, object]
    runtime_version: str = ATLAS_RUNTIME_VERSION
    provider_contract_version: str = ATLAS_PROVIDER_CONTRACT_VERSION

    @classmethod
    def create(
        cls,
        *,
        configuration: AtlasRuntimeConfigurationSnapshot,
        safe_logger: Logger,
        metrics: AtlasRuntimeMetrics,
        cancellation_signal: object,
        dependency_adapters: Mapping[str, object],
    ) -> AtlasRuntimeContext:
        return cls(
            configuration=configuration,
            safe_logger=safe_logger,
            metrics=metrics,
            cancellation_signal=cancellation_signal,
            dependency_adapters=MappingProxyType(dict(dependency_adapters)),
        )


class AtlasProvider(ABC):
    """Approved provider contract.

    `collect` is contract-only in Sprint 3.1. The Atlas runtime never invokes
    it, so no enterprise retrieval occurs from this subsystem.
    """

    definition: AtlasProviderDefinition

    @abstractmethod
    async def initialize(self, runtime_context: AtlasRuntimeContext) -> None:
        """Perform bounded provider startup using only the narrow context."""

    @abstractmethod
    async def health_check(self) -> AtlasProviderHealth:
        """Return a bounded, data-free health result without collection or LLM use."""

    @abstractmethod
    async def readiness_check(self) -> AtlasProviderReadiness:
        """Return current capability availability without enterprise retrieval."""

    @abstractmethod
    async def collect(
        self,
        request: AtlasProviderRequest,
        context: AtlasProviderCollectionContext,
    ) -> AtlasProviderResult:
        """Future-only collection contract; not called in Sprint 3.1."""

    async def drain(self) -> None:
        """Optional bounded drain hook for a future provider implementation."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Idempotent provider cleanup hook."""
