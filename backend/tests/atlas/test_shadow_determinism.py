import pytest

from app.shadow_mode import AtlasShadowModeService
from app.core.config import settings


@pytest.mark.asyncio
async def test_shadow_deterministic_fields_repeat_100_times(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_shadow_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    prompt = "System\nrules\n\nMemory\nprior"

    traces = [
        await service.execute(production_prompt=prompt, request_id="request-1")
        for _ in range(100)
    ]

    deterministic = {
        (
            trace.trace_id,
            trace.compilation_snapshot_fingerprint,
            trace.package_fingerprint,
            trace.forge_context_fingerprint,
            trace.provider_summary,
            trace.node_summary,
            trace.token_summary,
            trace.feature_flags,
            trace.comparison_summary,
        )
        for trace in traces
        if trace is not None
    }
    assert len(deterministic) == 1
    assert len(service.ring_buffer.snapshot()) == 100
