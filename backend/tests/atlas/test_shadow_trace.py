from pydantic import ValidationError
import pytest

from app.shadow_mode import AtlasShadowModeService
from app.core.config import settings


@pytest.mark.asyncio
async def test_shadow_trace_generated_and_contains_no_prompt_payload(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_shadow_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)

    trace = await service.execute(production_prompt="System secret\n\nMemory\nprior", request_id="request-1")

    assert trace is not None
    payload = trace.canonical_json()
    assert "System secret" not in payload
    assert "prior" not in payload
    assert trace.package_fingerprint
    assert trace.forge_context_fingerprint
    assert trace.feature_flags.shadow_enabled is True
    assert service.diagnostics()["shadow_traces"] == 1


def test_shadow_trace_is_immutable(shadow_trace_factory) -> None:
    trace = shadow_trace_factory("request-1")

    try:
        trace.request_id = "changed"
    except ValidationError:
        pass
    else:
        raise AssertionError("AtlasTrace must be immutable")
