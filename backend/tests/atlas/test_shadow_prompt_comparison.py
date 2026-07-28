from app.shadow_mode import compare_prompts
from app.forge.context_adapter import ForgeContextAdapter, estimate_text_tokens
from tests.forge.conftest import make_package


def test_prompt_comparison_counts_bytes_tokens_and_atlas_addition() -> None:
    atlas_package = make_package()
    window = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    prompt = "System\nrules\n\nMemory\nprior"

    comparison = compare_prompts(prompt, window)

    assert comparison.production_prompt_bytes == len(prompt.encode("utf-8"))
    assert comparison.shadow_prompt_bytes > comparison.production_prompt_bytes
    assert comparison.delta_bytes == comparison.shadow_prompt_bytes - comparison.production_prompt_bytes
    assert comparison.delta_tokens == comparison.shadow_prompt_tokens - comparison.production_prompt_tokens
    assert comparison.production_prompt_tokens == estimate_text_tokens(prompt)
    assert comparison.atlas_addition_count == 1
    assert comparison.shadow_section_count == comparison.production_section_count + 1
