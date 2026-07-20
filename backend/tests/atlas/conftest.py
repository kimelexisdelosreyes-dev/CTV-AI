from __future__ import annotations

import asyncio

import pytest

from app.atlas.models import (
    AtlasHealthStatus,
    AtlasProviderDefinition,
    AtlasProviderHealth,
    AtlasProviderReadiness,
)
from app.atlas.provider import AtlasProvider, AtlasRuntimeContext


class FakeAtlasProvider(AtlasProvider):
    def __init__(
        self,
        provider_id: str = "fixture_provider",
        *,
        required: bool = False,
        enabled: bool = True,
    ) -> None:
        self.definition = AtlasProviderDefinition(
            provider_id=provider_id,
            display_name="Fixture Provider",
            description="Atlas lifecycle test fixture.",
            version="1.2.3",
            capabilities=frozenset({"fixture_context"}),
            required=required,
            enabled_by_default=enabled,
            output_schema_version="1.0",
        )
        self.initialize_calls = 0
        self.health_calls = 0
        self.readiness_calls = 0
        self.drain_calls = 0
        self.shutdown_calls = 0
        self.initialize_delay = 0.0
        self.shutdown_delay = 0.0
        self.fail_initialize = False
        self.fail_health = False
        self.fail_readiness = False
        self.health_status = AtlasHealthStatus.HEALTHY

    async def initialize(self, _context: AtlasRuntimeContext) -> None:
        self.initialize_calls += 1
        if self.initialize_delay:
            await asyncio.sleep(self.initialize_delay)
        if self.fail_initialize:
            raise RuntimeError("private initialize failure")

    async def health_check(self) -> AtlasProviderHealth:
        self.health_calls += 1
        if self.fail_health:
            raise RuntimeError("private health failure")
        return AtlasProviderHealth(status=self.health_status)

    async def readiness_check(self) -> AtlasProviderReadiness:
        self.readiness_calls += 1
        if self.fail_readiness:
            raise RuntimeError("private readiness failure")
        return AtlasProviderReadiness(
            ready=True,
            available_capabilities=self.definition.capabilities,
        )

    async def collect(self, request, context):
        raise AssertionError("Atlas collection is out of scope for Sprint 3.1")

    async def drain(self) -> None:
        self.drain_calls += 1

    async def shutdown(self) -> None:
        self.shutdown_calls += 1
        if self.shutdown_delay:
            await asyncio.sleep(self.shutdown_delay)


@pytest.fixture
def atlas_settings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ctv_one_atlas_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_atlas_health_poll_enabled", False)
    monkeypatch.setattr(settings, "ctv_one_atlas_health_poll_seconds", 60.0)
    monkeypatch.setattr(settings, "ctv_one_atlas_health_timeout_seconds", 0.05)
    monkeypatch.setattr(settings, "ctv_one_atlas_initialize_timeout_seconds", 0.05)
    monkeypatch.setattr(settings, "ctv_one_atlas_shutdown_timeout_seconds", 0.05)
    monkeypatch.setattr(settings, "ctv_one_atlas_failure_threshold", 3)
    monkeypatch.setattr(settings, "ctv_one_atlas_recovery_threshold", 2)

