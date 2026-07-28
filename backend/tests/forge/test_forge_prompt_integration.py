from app.forge.context_adapter import ForgeContextAdapter
from app.forge.prompt_builder import integrate_atlas_context


BASE = "System\nrules\n\nConversation\nhello\n\nCompany Brain\nfacts\n\nMemory\nprior"


def test_disabled_prompt_is_byte_identical(atlas_package) -> None:
    window = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    assert integrate_atlas_context(BASE, window, atlas_enabled=False, forge_adapter_enabled=True) is BASE
    assert integrate_atlas_context(BASE, window, atlas_enabled=True, forge_adapter_enabled=False) is BASE
    assert integrate_atlas_context(BASE, None, atlas_enabled=True, forge_adapter_enabled=True) is BASE


def test_enabled_prompt_places_atlas_before_memory(atlas_package) -> None:
    window = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    prompt = integrate_atlas_context(BASE, window, atlas_enabled=True, forge_adapter_enabled=True)
    assert prompt.index("Company Brain") < prompt.index("Atlas Context") < prompt.index("Memory")
    assert window.package_fingerprint in prompt
