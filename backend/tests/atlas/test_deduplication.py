from datetime import datetime, timezone

from app.atlas.canonical import FrozenJson
from app.atlas.compiler.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import (
    AtlasClassification,
    AtlasCompilationSnapshot,
    AtlasCompilerPolicy,
    AtlasContextRequest,
    AtlasProvenance,
    AtlasProviderInputSnapshot,
    AtlasProviderSelectionEntry,
    AtlasProviderSelectionPlan,
)


def _provider_input(records: tuple[dict, ...]) -> AtlasProviderInputSnapshot:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return AtlasProviderInputSnapshot(
        provider_id="fixture",
        provider_version="1.0",
        provider_contract_version="1.0",
        result_schema_version="1.0",
        source_sequence=0,
        collected_at=now,
        capabilities=("knowledge_graph",),
        records=tuple(FrozenJson(record) for record in records),
        provenance=AtlasProvenance(
            provider_id="fixture",
            source_id="source_0",
            source_type="fixture",
            source_sequence=0,
            collected_at=now,
            original_reference="source_0",
            classification=AtlasClassification.INTERNAL,
            content_digest="a" * 64,
        ),
    )


def _snapshot(*records: dict) -> AtlasCompilationSnapshot:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    snapshot = AtlasCompilationSnapshot(
        request=AtlasContextRequest(request_id="request_1", intent="knowledge", requested_capabilities=("knowledge_graph",)),
        compiler_policy=AtlasCompilerPolicy(relationship_bonus_points=10),
        provider_selection_plan=AtlasProviderSelectionPlan(
            entries=(
                AtlasProviderSelectionEntry(
                    provider_id="fixture",
                    selected=True,
                    required=True,
                    requested_capabilities=("knowledge_graph",),
                    matched_capabilities=("knowledge_graph",),
                    ordinal=0,
                ),
            )
        ),
        provider_inputs=(_provider_input(tuple(records)),),
        compilation_time=now,
        source_configuration_fingerprint="b" * 64,
    )
    return snapshot.model_copy(update={"snapshot_fingerprint": snapshot.snapshot_fingerprint})


def test_exact_duplicates_are_excluded() -> None:
    result = AtlasContextCompiler().compile(
        _snapshot(
            {"id": "one", "title": "One", "content": "same", "source_reference": "ref_1"},
            {"id": "two", "title": "Two", "content": "same", "source_reference": "ref_1"},
        )
    )

    assert len(result.graph_nodes) == 1
    assert any("exact_duplicate" in decision.reason_categories for decision in result.manifest.entries)


def test_distinct_content_survives_deduplication() -> None:
    result = AtlasContextCompiler().compile(
        _snapshot(
            {"id": "one", "title": "One", "content": "first", "source_reference": "ref_1"},
            {"id": "two", "title": "Two", "content": "second", "source_reference": "ref_2"},
        )
    )

    assert len(result.graph_nodes) == 2


def test_duplicate_order_is_deterministic() -> None:
    records = (
        {"id": "one", "title": "One", "content": "same", "source_reference": "ref_1"},
        {"id": "two", "title": "Two", "content": "same", "source_reference": "ref_1"},
    )
    digests = [AtlasContextCompiler().compile(_snapshot(*records)).deterministic_digest for _ in range(12)]

    assert len(set(digests)) == 1
