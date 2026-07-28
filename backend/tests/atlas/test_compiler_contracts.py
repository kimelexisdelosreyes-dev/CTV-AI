from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.atlas.compiler_contracts import (
    AtlasAIRPackage,
    AtlasAIRRecord,
    AtlasClassification,
    AtlasCompilationSnapshot,
    AtlasCompilerPolicy,
    AtlasContextRequest,
    AtlasProvenance,
    AtlasProviderInputSnapshot,
    AtlasProviderSelectionPlan,
    AtlasScoreBreakdown,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def provenance() -> AtlasProvenance:
    return AtlasProvenance(
        provider_id="fixture_provider", source_id="source-1", source_type="fixture",
        source_sequence=0, collected_at=NOW, original_reference="reference-1",
        content_digest="a" * 64,
    )


def test_request_is_deeply_immutable_and_canonical() -> None:
    request = AtlasContextRequest(
        request_id="request-1", intent="summary", requested_capabilities=("zeta", "alpha"),
        metadata={"nested": {"value": 1}},
    )
    assert request.requested_capabilities == ("alpha", "zeta")
    assert request.metadata.to_python() == {"nested": {"value": 1}}
    returned = request.metadata.to_python()
    returned["nested"]["value"] = 2
    assert request.metadata.to_python() == {"nested": {"value": 1}}
    assert request.canonical_json() == request.canonical_json()


def test_snapshot_fingerprint_is_stable_for_shuffled_inputs() -> None:
    provider = AtlasProviderInputSnapshot(
        provider_id="fixture_provider", provider_version="1.0", provider_contract_version="1.0",
        result_schema_version="1.0", source_sequence=0, collected_at=NOW,
        records=({"b": 2, "a": 1},), provenance=provenance(),
    )
    snapshot = AtlasCompilationSnapshot(
        request=AtlasContextRequest(request_id="request-1", intent="summary"),
        compiler_policy=AtlasCompilerPolicy(), provider_selection_plan=AtlasProviderSelectionPlan(),
        provider_inputs=(provider,), compilation_time=NOW, source_configuration_fingerprint="b" * 64,
    )
    assert snapshot.snapshot_fingerprint == snapshot.deterministic_fingerprint()
    assert len(snapshot.snapshot_fingerprint) == 64


def test_air_is_flat_traceable_and_score_is_integer_only() -> None:
    air = AtlasAIRPackage(records=(AtlasAIRRecord(
        air_id="air-1", provider_id="fixture_provider", source_reference="reference-1",
        item_type="fact", normalized_title="Fact", confidence_points=10, provenance=provenance(), ordinal=0,
    ),))
    assert air.records[0].classification == AtlasClassification.INTERNAL
    assert AtlasScoreBreakdown(confidence_points=10, total_score_points=10).normalized_score == 0.01
    with pytest.raises(ValidationError):
        AtlasScoreBreakdown(confidence_points=10, total_score_points=9)
