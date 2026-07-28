from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.atlas.canonical import FrozenJson, canonical_bytes
from app.atlas.compiler.compiler import AtlasContextCompiler, _Graph
from app.atlas.compiler_contracts import (
    AtlasAIRItemType,
    AtlasAIRRecord,
    AtlasBudgetUsage,
    AtlasCompilationSnapshot,
    AtlasCompilerPolicy,
    AtlasConflict,
    AtlasContextRequest,
    AtlasProvenance,
    AtlasProviderInputSnapshot,
    AtlasProviderSelectionEntry,
    AtlasProviderSelectionPlan,
    AtlasRankedContextItem,
)
from app.atlas.context_package import (
    AtlasCitation,
    AtlasContextNode,
    AtlasContextPackage,
    AtlasContextRelationship,
    AtlasContextWarning,
    AtlasEvidenceItem,
)
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError


FIXED_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _provenance(provider_id: str, suffix: str) -> AtlasProvenance:
    return AtlasProvenance(
        provider_id=provider_id,
        source_id=f"source-{suffix}",
        source_type="fixture",
        source_sequence=0,
        collected_at=FIXED_TIME,
        original_reference=f"reference-{suffix}",
        content_digest=(suffix[0].lower() if suffix[0].lower() in "abcdef0123456789" else "a") * 64,
    )


def _pair(
    suffix: str,
    *,
    provider_id: str = "provider_a",
    content: str = "content",
) -> tuple[AtlasContextNode, AtlasAIRRecord]:
    provenance = _provenance(provider_id, suffix)
    record = AtlasAIRRecord(
        air_id=f"air-{suffix}",
        provider_id=provider_id,
        source_reference=f"reference-{suffix}",
        item_type=AtlasAIRItemType.RECORD,
        normalized_title=f"Record {suffix}",
        normalized_content=content,
        normalized_attributes=FrozenJson({}),
        confidence_points=0,
        freshness_at=FIXED_TIME,
        provenance=provenance,
        ordinal=0,
    )
    node = AtlasContextNode(
        node_id=f"node-{suffix}",
        node_type="record",
        label=f"Record {suffix}",
        provenance=provenance,
    )
    return node, record


def _graph(
    *pairs: tuple[AtlasContextNode, AtlasAIRRecord],
    relationships: tuple[AtlasContextRelationship, ...] = (),
) -> _Graph:
    return _Graph(
        nodes=tuple(node for node, _ in pairs),
        relationships=relationships,
        source_by_node={node.node_id: record for node, record in pairs},
    )


def _ranked(*pairs: tuple[AtlasContextNode, AtlasAIRRecord]) -> tuple[AtlasRankedContextItem, ...]:
    return tuple(
        AtlasRankedContextItem(
            item_id=node.node_id,
            provider_id=record.provider_id,
            total_score_points=100 - index,
            provider_priority_points=0,
            confidence_points=record.confidence_points,
            freshness_sort_value=int(FIXED_TIME.timestamp()),
            deterministic_rank=index,
            tie_break_values=(record.provider_id, node.node_id),
        )
        for index, (node, record) in enumerate(pairs, 1)
    )


def _provider_input(provider_id: str, index: int) -> AtlasProviderInputSnapshot:
    provenance = _provenance(provider_id, f"input-{index}")
    return AtlasProviderInputSnapshot(
        provider_id=provider_id,
        provider_version="1.0",
        provider_contract_version="1.0",
        result_schema_version="1.0",
        source_sequence=index,
        collected_at=FIXED_TIME,
        provenance=provenance,
    )


def _snapshot(
    *,
    providers: tuple[str, ...] = ("provider_a",),
    provider_inputs: tuple[AtlasProviderInputSnapshot, ...] = (),
    **policy_values: int,
) -> AtlasCompilationSnapshot:
    entries = tuple(
        AtlasProviderSelectionEntry(
            provider_id=provider_id,
            selected=True,
            ordinal=index,
        )
        for index, provider_id in enumerate(sorted(providers))
    )
    return AtlasCompilationSnapshot(
        request=AtlasContextRequest(request_id="request-budget", intent="summary"),
        compiler_policy=AtlasCompilerPolicy(**policy_values),
        provider_selection_plan=AtlasProviderSelectionPlan(entries=entries),
        provider_inputs=provider_inputs,
        compilation_time=FIXED_TIME,
        source_configuration_fingerprint="b" * 64,
    )


def _apply_budget(snapshot: AtlasCompilationSnapshot, graph: _Graph, pairs):
    return AtlasContextCompiler()._budget(snapshot, graph, _ranked(*pairs))


def _build_package(
    *,
    pairs: tuple[tuple[AtlasContextNode, AtlasAIRRecord], ...] = (),
    relationships: tuple[AtlasContextRelationship, ...] = (),
    conflicts: tuple[AtlasConflict, ...] = (),
    warnings: tuple[str, ...] = (),
    **policy_values: int,
):
    providers = tuple(sorted({record.provider_id for _, record in pairs})) or ("provider_a",)
    inputs = tuple(_provider_input(provider_id, index) for index, provider_id in enumerate(providers))
    snapshot = _snapshot(providers=providers, provider_inputs=inputs, **policy_values)
    graph = _graph(*pairs, relationships=relationships)
    compiler = AtlasContextCompiler()
    nodes, kept_relationships, usage, decisions, stage = compiler._budget(
        snapshot,
        graph,
        _ranked(*pairs),
    )
    manifest = compiler._manifest(snapshot, stage, inputs, conflicts, usage, warnings)
    package = compiler._package(
        snapshot,
        inputs,
        nodes,
        kept_relationships,
        conflicts,
        usage,
        manifest,
        warnings,
        len(decisions),
    )
    return snapshot, usage, decisions, package


def test_total_node_limit_selects_only_top_ranked_candidates():
    pairs = tuple(_pair(f"a{index}") for index in range(3))
    selected, _, usage, decisions, _ = _apply_budget(
        _snapshot(max_total_nodes=2),
        _graph(*pairs),
        pairs,
    )

    assert [node.node_id for node in selected] == ["node-a0", "node-a1"]
    assert usage.nodes == 2
    assert [decision.selected for decision in decisions] == [True, True, False]


def test_per_provider_node_limit_is_enforced_independently():
    pairs = (
        _pair("b1", provider_id="provider_a"),
        _pair("b2", provider_id="provider_a"),
        _pair("b3", provider_id="provider_b"),
    )
    selected, _, _, decisions, _ = _apply_budget(
        _snapshot(providers=("provider_a", "provider_b"), max_nodes_per_provider=1),
        _graph(*pairs),
        pairs,
    )

    assert [node.node_id for node in selected] == ["node-b1", "node-b3"]
    assert [decision.selected for decision in decisions] == [True, False, True]


def test_relationship_limit_is_applied_after_node_selection():
    pairs = (_pair("c1"), _pair("c2"), _pair("c3"))
    relationships = (
        AtlasContextRelationship(relationship_type="related_to", source_node_id="node-c1", target_node_id="node-c2"),
        AtlasContextRelationship(relationship_type="supports", source_node_id="node-c2", target_node_id="node-c3"),
    )
    _, selected_relationships, usage, _, _ = _apply_budget(
        _snapshot(max_total_relationships=1),
        _graph(*pairs, relationships=relationships),
        pairs,
    )

    assert selected_relationships == relationships[:1]
    assert usage.relationships == 1


def test_relationship_with_excluded_endpoint_is_not_retained():
    pairs = (_pair("c4"), _pair("c5"))
    relationship = AtlasContextRelationship(
        relationship_type="related_to",
        source_node_id="node-c4",
        target_node_id="node-c5",
    )

    _, selected_relationships, usage, _, _ = _apply_budget(
        _snapshot(max_total_nodes=1),
        _graph(*pairs, relationships=(relationship,)),
        pairs,
    )

    assert selected_relationships == ()
    assert usage.relationships == 0


def test_evidence_limit_is_applied_by_package_builder():
    pairs = (_pair("d1"), _pair("d2"), _pair("d3"))

    _, _, _, package = _build_package(pairs=pairs, max_total_evidence=1)

    assert len(package.evidence) == 1
    assert package.budgets.evidence_count == 1


def test_citation_limit_is_applied_by_package_builder():
    pairs = (_pair("d4"), _pair("d5"), _pair("d6"))

    _, _, _, package = _build_package(pairs=pairs, max_total_citations=1)

    assert len(package.citations) == 1


def test_aggregate_content_character_cost_is_enforced_before_selection():
    pairs = (_pair("e1", content="abc"), _pair("e2", content="def"))
    selected, _, usage, decisions, _ = _apply_budget(
        _snapshot(max_total_serialized_bytes=5),
        _graph(*pairs),
        pairs,
    )

    assert [node.node_id for node in selected] == ["node-e1"]
    assert usage.text_characters == 3
    assert [decision.selected for decision in decisions] == [True, False]


def test_per_node_content_limit_excludes_without_truncating_source():
    pair = _pair("e3", content="abcdef")
    graph = _graph(pair)
    selected, _, usage, decisions, _ = _apply_budget(
        _snapshot(max_content_chars_per_node=5),
        graph,
        (pair,),
    )

    assert selected == ()
    assert usage.text_characters == 0
    assert decisions[0].reason_category == "budget_exceeded"
    assert graph.source_by_node["node-e3"].normalized_content == "abcdef"


def test_package_serialized_byte_limit_raises_safe_atlas_category():
    pair = _pair("f1", content="x")

    with pytest.raises(AtlasRuntimeError) as caught:
        _build_package(pairs=(pair,), max_total_serialized_bytes=64)

    assert caught.value.category == AtlasErrorCategory.CONTRACT_SIZE_EXCEEDED
    assert str(caught.value) == "The Atlas contract exceeds its size limit."


def test_warning_collection_has_a_hard_contract_limit():
    warnings = tuple(
        AtlasContextWarning(category=f"warning_{index}", safe_message="safe")
        for index in range(65)
    )

    with pytest.raises(ValidationError, match="at most 64 items"):
        AtlasContextPackage(request_id="request-warning-limit", warnings=warnings)


def test_conflicts_are_preserved_by_budget_and_package_stages():
    pair = _pair("f2")
    conflict = AtlasConflict(
        conflict_id="conflict-f2",
        conflict_type="contradictory_fact",
        subject_key="subject-f2",
        item_ids=(pair[0].node_id,),
        provider_ids=("provider_a",),
        values=(FrozenJson("one"), FrozenJson("two")),
        provenance=(pair[1].provenance,),
    )

    _, usage, _, package = _build_package(pairs=(pair,), conflicts=(conflict,))

    assert usage.conflicts == 0
    assert package.conflicts == (conflict,)


def test_budget_exclusion_is_deterministic_when_graph_order_changes():
    pairs = (_pair("g1"), _pair("g2"), _pair("g3"))
    snapshot = _snapshot(max_total_nodes=2)
    compiler = AtlasContextCompiler()
    ranked = _ranked(*pairs)

    forward = compiler._budget(snapshot, _graph(*pairs), ranked)
    reverse = compiler._budget(snapshot, _graph(*reversed(pairs)), ranked)

    assert canonical_bytes(forward) == canonical_bytes(reverse)


def test_budget_decision_exists_for_every_candidate_with_exact_accounting():
    pairs = (_pair("g4"), _pair("g5"), _pair("g6"))
    _, _, usage, decisions, stage = _apply_budget(
        _snapshot(max_total_nodes=1),
        _graph(*pairs),
        pairs,
    )

    assert len(decisions) == len(stage) == len(pairs)
    assert [(item.usage_before, item.item_cost, item.usage_after) for item in decisions] == [
        (0, 1, 1),
        (1, 0, 1),
        (1, 0, 1),
    ]
    assert usage.nodes == decisions[-1].usage_after


def test_stricter_node_budget_is_monotonic():
    pairs = tuple(_pair(f"h{index}") for index in range(4))
    graph = _graph(*pairs)
    compiler = AtlasContextCompiler()
    ranked = _ranked(*pairs)

    generous, *_ = compiler._budget(_snapshot(max_total_nodes=3), graph, ranked)
    strict, *_ = compiler._budget(_snapshot(max_total_nodes=1), graph, ranked)

    assert {node.node_id for node in strict}.issubset({node.node_id for node in generous})
    assert len(strict) == 1
    assert len(generous) == 3


def test_successful_package_size_uses_actual_canonical_utf8_measurement():
    pair = _pair("h4", content="Chinoy context")

    _, _, _, package = _build_package(pairs=(pair,))

    assert package.serialized_bytes() == len(package.deterministic_json().encode("utf-8"))
    assert package.serialized_bytes() == len(canonical_bytes(package.deterministic_content()))


def test_evidence_contract_rejects_more_than_global_maximum():
    evidence = tuple(
        AtlasEvidenceItem(
            evidence_id=f"evidence-{index}",
            provider_id="provider_a",
            excerpt="safe",
            classification="internal",
        )
        for index in range(257)
    )

    with pytest.raises(ValidationError, match="at most 256 items"):
        AtlasContextPackage(request_id="request-evidence-limit", evidence=evidence)


def test_citation_contract_rejects_more_than_global_maximum():
    citations = tuple(
        AtlasCitation(
            citation_id=f"citation-{index}",
            provider_id="provider_a",
            source_reference=f"reference-{index}",
            label="safe",
        )
        for index in range(257)
    )

    with pytest.raises(ValidationError, match="at most 256 items"):
        AtlasContextPackage(request_id="request-citation-limit", citations=citations)


def test_conflict_contract_rejects_more_than_global_maximum():
    conflicts = tuple(
        AtlasConflict(
            conflict_id=f"conflict-{index}",
            conflict_type="contradictory_fact",
            subject_key=f"subject-{index}",
            item_ids=(),
            provider_ids=(),
        )
        for index in range(65)
    )

    with pytest.raises(ValidationError, match="at most 64 items"):
        AtlasContextPackage(request_id="request-conflict-limit", conflicts=conflicts)
