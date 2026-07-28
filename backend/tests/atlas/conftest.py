from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from app.shadow_mode import (
    AtlasTrace,
    AtlasTraceCanarySummary,
    AtlasTraceComparisonSummary,
    AtlasTraceFeatureFlags,
    AtlasTraceLifecycleSummary,
    AtlasTraceNodeSummary,
    AtlasTraceProviderSummary,
    AtlasTraceTimingSummary,
    AtlasTraceTokenSummary,
)
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
    monkeypatch.setattr(settings, "ctv_one_atlas_shadow_enabled", False)
    monkeypatch.setattr(settings, "ctv_one_atlas_canary_enabled", False)
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", False)


@pytest_asyncio.fixture
async def initialized_runtime(atlas_settings):
    runtime = AtlasRuntimeManager(AtlasProviderRegistry())
    await runtime.initialize()
    yield runtime
    await runtime.shutdown()


@pytest.fixture
def shadow_trace_factory():
    def factory(request_id: str) -> AtlasTrace:
        return AtlasTrace(
            trace_id=f"trace-{request_id}",
            request_id=request_id,
            compilation_snapshot_fingerprint="a" * 64,
            package_fingerprint="b" * 64,
            manifest_reference={"manifest_digest": "c" * 64},
            forge_context_fingerprint="d" * 64,
            provider_summary=AtlasTraceProviderSummary(
                registered_providers=0,
                selected_providers=0,
                successful=0,
                partial=0,
                failed=0,
                timeouts=0,
            ),
            node_summary=AtlasTraceNodeSummary(
                compiled_nodes=0,
                retained_nodes=0,
                dropped_nodes=0,
            ),
            token_summary=AtlasTraceTokenSummary(
                estimated_package_tokens=1,
                estimated_forge_tokens=0,
                budget=4000,
                retained=0,
                dropped=0,
            ),
            timing_summary=AtlasTraceTimingSummary(
                provider_orchestration_ms=0,
                compiler_ms=0,
                adapter_ms=0,
                comparison_ms=0,
                trace_ms=0,
                total_ms=0,
            ),
            lifecycle_summary=AtlasTraceLifecycleSummary(
                runtime_state="ready",
                shadow_enabled=True,
                adapter_enabled=True,
                compiler_ready=True,
            ),
            feature_flags=AtlasTraceFeatureFlags(
                shadow_enabled=True,
                canary_enabled=False,
                live_enabled=False,
                canary_percentage=0,
            ),
            canary_summary=AtlasTraceCanarySummary(
                policy_decision="shadow_only",
                canary_eligible=False,
                feature_source="canary_disabled",
                fallback_reason="canary_disabled",
                atlas_active=False,
                live_active=False,
                atlas_injected=False,
                rollback_active=False,
            ),
            comparison_summary=AtlasTraceComparisonSummary(
                production_prompt_bytes=1,
                shadow_prompt_bytes=2,
                delta_bytes=1,
                production_prompt_tokens=1,
                shadow_prompt_tokens=1,
                delta_tokens=0,
                production_section_count=1,
                shadow_section_count=2,
                atlas_addition_count=1,
                atlas_context_bytes=1,
                atlas_context_tokens=1,
            ),
        )

    return factory
