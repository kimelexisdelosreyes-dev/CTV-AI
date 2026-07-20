from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.atlas.errors import AtlasErrorCategory, AtlasProviderRegistrationError
from app.atlas.models import AtlasProviderDefinition
from app.atlas.registry import AtlasProviderRegistry

from .conftest import FakeAtlasProvider


def test_registry_accepts_valid_static_provider_and_exposes_immutable_definition() -> None:
    registry = AtlasProviderRegistry()
    provider = FakeAtlasProvider()
    registry.register(provider)

    assert registry.get("fixture_provider") is provider
    assert registry.definitions() == (provider.definition,)
    with pytest.raises(ValidationError):
        provider.definition.display_name = "Changed"  # type: ignore[misc]


def test_registry_rejects_duplicate_and_incompatible_contracts() -> None:
    registry = AtlasProviderRegistry()
    registry.register(FakeAtlasProvider())
    with pytest.raises(AtlasProviderRegistrationError) as duplicate:
        registry.register(FakeAtlasProvider())
    assert duplicate.value.category == AtlasErrorCategory.PROVIDER_DUPLICATE

    incompatible = FakeAtlasProvider("incompatible_provider")
    incompatible.definition = incompatible.definition.model_copy(
        update={"contract_version": "2.0"}
    )
    with pytest.raises(AtlasProviderRegistrationError) as mismatch:
        registry.register(incompatible)
    assert mismatch.value.category == AtlasErrorCategory.PROVIDER_CONTRACT_MISMATCH


@pytest.mark.parametrize(
    "updates",
    [
        {"provider_id": "Not Stable"},
        {"version": "v1"},
        {"capabilities": frozenset({"not-stable"})},
        {"default_timeout_seconds": 61.0, "max_timeout_seconds": 60.0},
    ],
)
def test_provider_definition_rejects_invalid_values(updates) -> None:
    values = FakeAtlasProvider().definition.model_dump()
    values.update(updates)
    with pytest.raises(ValidationError):
        AtlasProviderDefinition.model_validate(values)


def test_registry_is_empty_by_default_and_unregister_is_test_controlled_only() -> None:
    registry = AtlasProviderRegistry()
    assert registry.definitions() == ()
    registry.register(FakeAtlasProvider())
    registry.unregister("fixture_provider")
    assert len(registry) == 0

    registry.register(FakeAtlasProvider())
    registry.begin_runtime_initialization()
    with pytest.raises(AtlasProviderRegistrationError):
        registry.unregister("fixture_provider")
