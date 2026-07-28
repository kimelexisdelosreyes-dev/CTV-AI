import pytest

from app.shadow_mode import AtlasShadowModeService, production_prompt_from_messages
from app.core.config import settings
from app.services.ai_router import AIRouter


@pytest.mark.asyncio
async def test_shadow_on_executes_atlas_without_changing_llm_messages(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_shadow_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    messages = AIRouter.build_messages([{"role": "user", "content": "hello"}], "general")
    before = [dict(item) for item in messages]

    trace = await service.execute(
        production_prompt=production_prompt_from_messages(messages),
        request_id="request-1",
    )

    assert trace is not None
    assert messages == before
    assert initialized_runtime.compilation_metrics.compilation_successes >= 1
