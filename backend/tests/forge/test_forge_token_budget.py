from app.forge.context_adapter import ForgeContextAdapter, estimate_text_tokens

from .conftest import make_package


def test_token_estimation_is_stable() -> None:
    assert estimate_text_tokens("abcdefgh") == 2
    assert estimate_text_tokens("abcdefgh") == estimate_text_tokens("abcdefgh")


def test_budget_retains_highest_ranked_prefix_deterministically() -> None:
    package = make_package(node_count=4, content_chars=20)
    one = ForgeContextAdapter(token_budget=9, atlas_enabled=True, adapter_enabled=True).adapt(package)
    two = ForgeContextAdapter(token_budget=9, atlas_enabled=True, adapter_enabled=True).adapt(package)
    assert tuple(block.node_id for block in one.context_blocks) == ("node-0",)
    assert one.dropped_node_count == 3
    assert one.canonical_bytes() == two.canonical_bytes()
