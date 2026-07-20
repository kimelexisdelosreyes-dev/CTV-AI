from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.atlas.context_package import create_empty_context_package, validate_context_package
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from app.atlas.models import AtlasProviderResult
from app.atlas.metrics import atlas_runtime_metrics


def test_empty_context_package_is_valid_and_serialization_is_deterministic() -> None:
    package = create_empty_context_package("request-1")
    assert package.contract_version == "1.0"
    assert package.deterministic_json() == package.deterministic_json()
    assert any(
        name.startswith("atlas_context_package_created_count")
        for name in atlas_runtime_metrics.safe_snapshot()["counters"]
    )


def test_context_package_rejects_invalid_contract_provider_result_and_metadata() -> None:
    with pytest.raises(AtlasRuntimeError) as invalid_contract:
        validate_context_package({"request_id": "request-1", "contract_version": "2.0"})
    assert invalid_contract.value.category == AtlasErrorCategory.CONTEXT_PACKAGE_INVALID

    with pytest.raises(AtlasRuntimeError):
        validate_context_package(
            {
                "request_id": "request-1",
                "selected_provider_ids": [],
                "provider_results": [
                    {
                        "provider_id": "fixture_provider",
                        "output_schema_version": "1.0",
                        "data": {},
                    }
                ],
            }
        )
    with pytest.raises(AtlasRuntimeError):
        validate_context_package(
            {
                "request_id": "request-1",
                "metadata": {"prompt": "must never be stored"},
            }
        )


def test_context_package_rejects_non_json_objects_and_bounds_provider_results() -> None:
    with pytest.raises(ValidationError):
        AtlasProviderResult(
            provider_id="fixture_provider",
            data={"exception": RuntimeError("private")},
        )
    with pytest.raises(ValidationError):
        AtlasProviderResult(
            provider_id="fixture_provider",
            data={"secret_value": "must not be retained"},
        )
    with pytest.raises(ValidationError):
        AtlasProviderResult(
            provider_id="fixture_provider",
            data={"text": "x" * 40_000},
        )


def test_context_nodes_relationships_and_citations_must_reference_package_members() -> None:
    with pytest.raises(AtlasRuntimeError):
        validate_context_package(
            {
                "request_id": "request-1",
                "relationships": [
                    {
                        "relationship_type": "supports",
                        "source_node_id": "missing",
                        "target_node_id": "also_missing",
                    }
                ],
            }
        )
    with pytest.raises(AtlasRuntimeError):
        validate_context_package(
            {
                "request_id": "request-1",
                "evidence": [
                    {
                        "evidence_id": "evidence-1",
                        "provider_id": "fixture_provider",
                        "excerpt": "bounded evidence",
                        "classification": "internal",
                        "citation_ids": ["missing-citation"],
                    }
                ],
            }
        )
