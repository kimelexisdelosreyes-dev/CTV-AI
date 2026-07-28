import pytest

from app.forge.context_adapter import ForgeContextAdapter
from app.forge.errors import ForgeContextError, ForgeContextErrorCategory


@pytest.mark.parametrize(
    ("atlas_enabled", "adapter_enabled", "category"),
    [
        (False, False, ForgeContextErrorCategory.ADAPTER_DISABLED),
        (True, False, ForgeContextErrorCategory.ADAPTER_DISABLED),
        (False, True, ForgeContextErrorCategory.ATLAS_DISABLED),
    ],
)
def test_disabled_flag_combinations_fail_safely(atlas_package, atlas_enabled, adapter_enabled, category) -> None:
    adapter = ForgeContextAdapter(token_budget=100, atlas_enabled=atlas_enabled, adapter_enabled=adapter_enabled)
    assert not adapter.available
    with pytest.raises(ForgeContextError) as exc:
        adapter.adapt(atlas_package)
    assert exc.value.category == category


def test_both_flags_enable_adapter(atlas_package) -> None:
    adapter = ForgeContextAdapter(token_budget=100, atlas_enabled=True, adapter_enabled=True)
    assert adapter.available
    assert adapter.adapt(atlas_package).retained_node_count == 3
