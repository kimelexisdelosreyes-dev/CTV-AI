import pytest

from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


@pytest.mark.asyncio
async def test_live_prompt_places_atlas_before_memory(monkeypatch, initialized_runtime) -> None:
    monkeypatch.setattr(settings, "ctv_one_atlas_live_enabled", True)
    service = AtlasShadowModeService(initialized_runtime)
    system = "System\nrules\n\nConversation\nhello\n\nCompany Brain\nfacts\n\nMemory\nprior"

    routed, _, _ = await service.route_messages(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": "hello"}],
        request_id="request-1",
        user_identifier="employee",
    )

    content = routed[0]["content"]
    assert content.index("Company Brain") < content.index("Atlas Context") < content.index("Memory")
    assert content.startswith("System\nrules")
