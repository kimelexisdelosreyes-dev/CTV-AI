from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.atlas.models import AtlasProviderResult
from app.atlas.provider_orchestration import AtlasProviderExecutionPlan, AtlasProviderExecutionRequest
from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from .conftest import FakeAtlasProvider

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class CollectionProvider(FakeAtlasProvider):
    def __init__(self, provider_id="fixture_provider", *, result=None, delay=0.0, fail=False, required=False):
        super().__init__(provider_id, required=required); self.result = result; self.delay = delay; self.fail = fail
        self.collect_calls = 0; self.last_request = None; self.last_context = None

    async def collect(self, request, context):
        self.collect_calls += 1; self.last_request = request; self.last_context = context
        if self.delay: await asyncio.sleep(self.delay)
        if self.fail: raise RuntimeError("private provider failure")
        return self.result or AtlasProviderResult(provider_id=self.definition.provider_id, data={"records":[{"id":f"{self.definition.provider_id}-1", "title":"Title", "content":"Content"}]})


def execution_request(*plans, intent="summary"):
    if not plans: plans = (AtlasProviderExecutionPlan(provider_id="fixture_provider", capabilities=("fixture_context",)),)
    return AtlasProviderExecutionRequest(request_id="request-1", compilation_time=FIXED_TIME, selected_provider_plans=plans, intent=intent, capabilities=("fixture_context",), source_configuration_fingerprint="b" * 64)


def runtime_with(*providers):
    registry = AtlasProviderRegistry()
    for provider in providers: registry.register(provider)
    return AtlasRuntimeManager(registry)
