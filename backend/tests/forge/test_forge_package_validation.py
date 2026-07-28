import pytest

from app.forge.context_adapter import ForgeContextAdapter
from app.forge.errors import ForgeContextError, ForgeContextErrorCategory


def adapter() -> ForgeContextAdapter:
    return ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True)


def test_rejects_tampered_fingerprint(atlas_package) -> None:
    tampered = atlas_package.model_copy(update={"package_fingerprint": "f" * 64})
    with pytest.raises(ForgeContextError) as exc:
        adapter().adapt(tampered)
    assert exc.value.category == ForgeContextErrorCategory.PACKAGE_FINGERPRINT_INVALID


def test_rejects_missing_or_invalid_manifest_reference(atlas_package) -> None:
    missing = atlas_package.model_copy(update={"manifest_reference": None})
    missing = missing.model_copy(update={"package_fingerprint": missing.computed_fingerprint()})
    with pytest.raises(ForgeContextError) as exc:
        adapter().adapt(missing)
    assert exc.value.category == ForgeContextErrorCategory.MANIFEST_REFERENCE_INVALID


def test_rejects_unsupported_package_version(atlas_package) -> None:
    unsupported = atlas_package.model_copy(update={"contract_version": "1.0"})
    unsupported = unsupported.model_copy(update={"package_fingerprint": unsupported.computed_fingerprint()})
    with pytest.raises(ForgeContextError) as exc:
        adapter().adapt(unsupported)
    assert exc.value.category == ForgeContextErrorCategory.PACKAGE_VERSION_UNSUPPORTED


def test_rejects_noncanonical_node_order(atlas_package) -> None:
    changed = atlas_package.model_copy(update={"nodes": tuple(reversed(atlas_package.nodes)), "package_fingerprint": ""})
    changed = changed.model_copy(update={"package_fingerprint": changed.computed_fingerprint()})
    with pytest.raises(ForgeContextError) as exc:
        adapter().adapt(changed)
    assert exc.value.category == ForgeContextErrorCategory.PACKAGE_INVALID
