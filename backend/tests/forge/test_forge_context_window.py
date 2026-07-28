import pytest
from pydantic import ValidationError

from app.forge.context_adapter import ForgeContextAdapter


def test_window_is_deeply_immutable_and_canonical(atlas_package) -> None:
    window = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    with pytest.raises(ValidationError):
        window.retained_node_count = 9
    with pytest.raises(ValidationError):
        window.context_blocks[0].title = "changed"
    assert window.canonical_bytes() == window.model_copy().canonical_bytes()


def test_window_counts_and_tokens_are_consistent(atlas_package) -> None:
    window = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    assert window.retained_node_count == len(window.context_blocks)
    assert window.dropped_node_count == len(atlas_package.nodes) - len(window.context_blocks)
    assert window.estimated_tokens == sum(item.estimated_tokens for item in window.context_blocks)
