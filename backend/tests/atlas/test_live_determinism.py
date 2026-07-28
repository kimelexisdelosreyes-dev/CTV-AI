import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_live_deterministic_artifacts_repeat_100_times(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]

    traces = [
        (
            await service.route_messages(
                messages=messages,
                request_id="request-1",
                user_identifier="employee",
            )
        )[1]
        for _ in range(100)
    ]

    artifacts = {
        (
            trace.compilation_snapshot_fingerprint,
            trace.package_fingerprint,
            trace.forge_context_fingerprint,
            trace.canary_summary,
            trace.comparison_summary,
        )
        for trace in traces
        if trace is not None
    }
    assert len(artifacts) == 1
