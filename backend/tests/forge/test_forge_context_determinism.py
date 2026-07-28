from app.forge.context_adapter import ForgeContextAdapter


def test_one_package_consumed_one_hundred_times_is_byte_identical(atlas_package) -> None:
    adapter = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True)
    baseline = adapter.adapt(atlas_package).canonical_bytes()
    assert all(adapter.adapt(atlas_package).canonical_bytes() == baseline for _ in range(100))
