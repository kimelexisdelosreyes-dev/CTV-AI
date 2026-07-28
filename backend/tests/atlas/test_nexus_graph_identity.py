import pytest

from app.atlas.providers.nexus import (
    NexusGraphInfrastructureError,
    deterministic_entity_id,
    deterministic_relationship_id,
    normalize_nexus_identifier,
)


def test_equivalent_identifiers_normalize_identically() -> None:
    assert normalize_nexus_identifier("  External-Key  ") == "external_key"
    assert deterministic_entity_id("Team A", "Person", " Alice-01 ") == "team_a:person:alice_01"


def test_malformed_identifier_rejected() -> None:
    with pytest.raises(NexusGraphInfrastructureError):
        normalize_nexus_identifier("")


def test_relationship_id_is_deterministic() -> None:
    first = deterministic_relationship_id("Nexus", "a:person:1", "Reports-To", "a:person:2")
    second = deterministic_relationship_id(" nexus ", "a:person:1", "reports_to", "a:person:2")
    assert first == second
