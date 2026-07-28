from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest
from pydantic import ValidationError

from app.atlas.canonical import FrozenJson
from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import (
    AtlasAIRItemType,
    AtlasClassification,
    AtlasCompilationSnapshot,
    AtlasCompilerPolicy,
    AtlasCompilerStage,
    AtlasContextRequest,
    AtlasProvenance,
    AtlasProviderInputSnapshot,
    AtlasProviderSelectionEntry,
    AtlasProviderSelectionPlan,
    AtlasSelectionAction,
)
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError


NOW = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)


def _provider(
    records: tuple[object, ...],
    *,
    provider_id: str = "alpha_provider",
    source_sequence: int = 3,
    classification: AtlasClassification = AtlasClassification.INTERNAL,
    provenance_classification: AtlasClassification = AtlasClassification.INTERNAL,
    capabilities: tuple[str, ...] = ("summary",),
) -> AtlasProviderInputSnapshot:
    return AtlasProviderInputSnapshot(
        provider_id=provider_id,
        provider_version="1.0",
        provider_contract_version="1.0",
        result_schema_version="1.0",
        source_sequence=source_sequence,
        collected_at=NOW,
        capabilities=capabilities,
        records=records,
        provenance=AtlasProvenance(
            provider_id=provider_id,
            source_id=f"source-{provider_id}",
            source_type="fixture",
            source_sequence=99,
            collected_at=NOW,
            original_reference=f"reference-{provider_id}",
            transformation_steps=("fixture_normalization",),
            classification=provenance_classification,
            content_digest="f" * 64,
        ),
        classification=classification,
    )


def _snapshot(
    inputs: tuple[AtlasProviderInputSnapshot, ...],
    *,
    required_provider_ids: tuple[str, ...] = (),
) -> AtlasCompilationSnapshot:
    provider_ids = tuple(sorted({source.provider_id for source in inputs}))
    entries = tuple(
        AtlasProviderSelectionEntry(
            provider_id=provider_id,
            selected=True,
            required=provider_id in required_provider_ids,
            ordinal=index,
        )
        for index, provider_id in enumerate(provider_ids)
    )
    return AtlasCompilationSnapshot(
        request=AtlasContextRequest(request_id="request-air", intent="summary"),
        compiler_policy=AtlasCompilerPolicy(),
        provider_selection_plan=AtlasProviderSelectionPlan(entries=entries),
        provider_inputs=inputs,
        compilation_time=NOW,
        source_configuration_fingerprint="1" * 64,
    )


def _normalize(source: AtlasProviderInputSnapshot, *, required: bool = False):
    snapshot = _snapshot(
        (source,),
        required_provider_ids=(source.provider_id,) if required else (),
    )
    return AtlasContextCompiler()._normalize(snapshot, (source,))


def test_normalize_converts_a_generic_mapping_to_a_flat_air_record() -> None:
    source = _provider(
        (
            {
                "id": "fact-1",
                "item_type": "fact",
                "title": "A Fact",
                "content": "A deterministic fact.",
                "confidence_points": 21,
            },
        )
    )

    air, decisions = _normalize(source)

    assert len(air.records) == 1
    assert air.records[0].item_type == AtlasAIRItemType.FACT
    assert air.records[0].normalized_title == "A Fact"
    assert air.records[0].normalized_content == "A deterministic fact."
    assert air.records[0].confidence_points == 21
    assert decisions[0].stage == AtlasCompilerStage.NORMALIZATION
    assert decisions[0].action == AtlasSelectionAction.SELECTED


def test_normalize_uses_the_documented_stable_air_identifier() -> None:
    source = _provider(
        ({"item_type": "fact", "title": "Stable", "content": "value"},)
    )
    expected_digest = hashlib.sha256(
        "alpha_provider|reference-alpha_provider|fact|Stable|value".encode()
    ).hexdigest()

    first, _ = _normalize(source)
    second, _ = _normalize(source)

    assert first.records[0].air_id == f"air-{expected_digest[:24]}"
    assert first.records[0].air_id == second.records[0].air_id


def test_normalize_canonicalizes_air_record_order_and_ordinals() -> None:
    source = _provider(
        (
            {"id": "zeta", "title": "Zeta", "content": "z"},
            {"id": "alpha", "title": "Alpha", "content": "a"},
        )
    )

    air, _ = _normalize(source)

    assert tuple(record.air_id for record in air.records) == tuple(
        sorted(record.air_id for record in air.records)
    )
    assert tuple(record.ordinal for record in air.records) == (0, 1)


def test_normalize_preserves_provider_ownership_and_source_sequence() -> None:
    source = _provider(({"id": "owned", "content": "value"},), source_sequence=7)

    air, _ = _normalize(source)
    record = air.records[0]

    assert record.provider_id == "alpha_provider"
    assert record.provenance.provider_id == "alpha_provider"
    assert record.provenance.source_sequence == 7


def test_normalize_strips_and_bounds_titles_with_empty_fallback() -> None:
    long_title = "  " + ("T" * 600) + "  "
    source = _provider(
        (
            {"id": "long", "title": long_title},
            {"id": "empty", "title": "   "},
        )
    )

    air, _ = _normalize(source)
    titles = {record.normalized_title for record in air.records}

    assert "T" * 512 in titles
    assert "record" in titles
    assert all(title == title.strip() and 1 <= len(title) <= 512 for title in titles)


def test_normalize_strips_and_bounds_content_without_hidden_rewriting() -> None:
    content = "  " + ("x" * 16_100) + "  "
    source = _provider(({"id": "large", "content": content},))

    air, _ = _normalize(source)

    assert air.records[0].normalized_content == "x" * 16_000


def test_normalize_canonicalizes_and_deeply_freezes_attributes() -> None:
    source = _provider(
        ({"id": "attrs", "attributes": {"z": 2, "a": {"b": 1}}},)
    )

    air, _ = _normalize(source)
    attributes = air.records[0].normalized_attributes
    returned = attributes.to_python()
    returned["a"]["b"] = 99

    assert list(attributes.to_python()) == ["a", "z"]
    assert attributes.to_python() == {"a": {"b": 1}, "z": 2}
    assert FrozenJson({"z": 2, "a": {"b": 1}}) == attributes


def test_normalize_propagates_the_most_restrictive_classification() -> None:
    source = _provider(
        ({"id": "classified"},),
        classification=AtlasClassification.CONFIDENTIAL,
        provenance_classification=AtlasClassification.RESTRICTED,
    )

    air, _ = _normalize(source)

    assert air.records[0].classification == AtlasClassification.RESTRICTED


def test_normalize_propagates_canonical_capabilities() -> None:
    source = _provider(
        ({"id": "capable"},), capabilities=("zeta_capability", "alpha_capability")
    )

    air, _ = _normalize(source)

    assert air.records[0].capability_ids == (
        "alpha_capability",
        "zeta_capability",
    )


def test_normalize_preserves_provenance_fields_and_has_stable_digest() -> None:
    source = _provider(({"id": "traceable", "content": "same"},))

    first, _ = _normalize(source)
    second, _ = _normalize(source)
    provenance = first.records[0].provenance

    assert provenance.source_id == source.provenance.source_id
    assert provenance.original_reference == source.provenance.original_reference
    assert provenance.content_digest == source.provenance.content_digest
    assert provenance.transformation_steps == ("fixture_normalization",)
    assert first.deterministic_fingerprint() == second.deterministic_fingerprint()


def test_normalize_excludes_a_malformed_optional_record_with_a_decision() -> None:
    source = _provider((["not", "a", "mapping"],))

    air, decisions = _normalize(source, required=False)

    assert air.records == ()
    assert len(decisions) == 1
    assert decisions[0].action == AtlasSelectionAction.EXCLUDED
    assert decisions[0].reason_categories == ("provider_record_invalid",)


def test_normalize_rejects_a_malformed_required_record_safely() -> None:
    source = _provider((["not", "a", "mapping"],))

    with pytest.raises(AtlasRuntimeError) as raised:
        _normalize(source, required=True)

    assert raised.value.category == AtlasErrorCategory.PROVIDER_INPUT_INVALID
    assert str(raised.value) == "The Atlas provider input is invalid."


def test_provider_record_contract_rejects_unsafe_nested_metadata_keys() -> None:
    with pytest.raises(ValidationError, match="prohibited field name"):
        _provider(
            (
                {
                    "id": "unsafe",
                    "attributes": {"nested": {"credential_token": "redacted"}},
                },
            )
        )


def test_provider_record_contract_rejects_arbitrary_python_objects() -> None:
    class _OpaqueValue:
        pass

    with pytest.raises(TypeError, match="JSON-safe"):
        _provider(({"id": "unsafe", "attributes": {"opaque": _OpaqueValue()}},))


def test_relation_candidate_remains_flat_without_adjacency_data() -> None:
    source = _provider(
        (
            {
                "id": "relation-1",
                "item_type": "relation_candidate",
                "attributes": {
                    "source_air_id": "air-source",
                    "target_air_id": "air-target",
                    "relationship_type": "related_to",
                },
            },
        )
    )

    air, _ = _normalize(source)
    record = air.records[0]

    assert record.item_type == AtlasAIRItemType.RELATION_CANDIDATE
    assert record.normalized_attributes.to_python()["source_air_id"] == "air-source"
    assert not ({"edges", "neighbors", "adjacency"} & set(type(record).model_fields))


def test_shuffled_records_produce_byte_identical_air() -> None:
    records = (
        {"id": "one", "title": "One", "content": "first"},
        {"id": "two", "title": "Two", "content": "second"},
        {"id": "three", "title": "Three", "content": "third"},
    )
    first_source = _provider(records)
    second_source = _provider(tuple(reversed(records)))

    first, _ = _normalize(first_source)
    second, _ = _normalize(second_source)

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.deterministic_fingerprint() == second.deterministic_fingerprint()
