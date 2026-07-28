import pytest

from app.shadow_mode import AtlasShadowModeService, production_prompt_from_messages
from app.core.config import settings


@pytest.mark.asyncio
async def test_no_atlas_context_reaches_llm_payload(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_shadow_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]

    trace = await service.execute(
        production_prompt=production_prompt_from_messages(messages),
        request_id="request-1",
    )

    assert trace is not None
    assert "Atlas Context" not in str(messages)
    assert messages == [{"role": "system", "content": "System"}, {"role": "user", "content": "hello"}]
