from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.atlas.canonical import FrozenJson, canonical_json
from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import (
    AtlasAIRItemType,
    AtlasAIRPackage,
    AtlasAIRRecord,
    AtlasClassification,
    AtlasCompilerStage,
    AtlasProvenance,
    AtlasSelectionAction,
)


FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _provenance(
    provider_id: str = "alpha_provider",
    *,
    source_id: str = "source-alpha",
    classification: AtlasClassification = AtlasClassification.INTERNAL,
) -> AtlasProvenance:
    return AtlasProvenance(
        provider_id=provider_id,
        source_id=source_id,
        source_type="fixture",
        source_sequence=0,
        collected_at=FIXED_TIME,
        original_reference=f"reference-{source_id}",
        classification=classification,
        content_digest="a" * 64,
    )


def _record(
    air_id: str,
    *,
    provider_id: str = "alpha_provider",
    item_type: AtlasAIRItemType = AtlasAIRItemType.RECORD,
    attributes: object | None = None,
    classification: AtlasClassification = AtlasClassification.INTERNAL,
    ordinal: int = 0,
    provenance: AtlasProvenance | None = None,
) -> AtlasAIRRecord:
    return AtlasAIRRecord(
        air_id=air_id,
        provider_id=provider_id,
        source_reference=f"reference-{air_id}",
        item_type=item_type,
        normalized_title=f"Title {air_id}",
        normalized_content=f"Content {air_id}",
        normalized_attributes=FrozenJson(attributes or {}),
        confidence_points=10,
        freshness_at=FIXED_TIME,
        classification=classification,
        provenance=provenance
        or _provenance(
            provider_id,
            source_id=f"source-{air_id}",
            classification=classification,
        ),
        ordinal=ordinal,
    )


def _relation(
    air_id: str,
    source_air_id: str,
    target_air_id: str,
    *,
    relationship_type: str = "related_to",
    provider_id: str = "alpha_provider",
    ordinal: int = 0,
    classification: AtlasClassification = AtlasClassification.INTERNAL,
) -> AtlasAIRRecord:
    return _record(
        air_id,
        provider_id=provider_id,
        item_type=AtlasAIRItemType.RELATION_CANDIDATE,
        attributes={
            "relationship_type": relationship_type,
            "source_air_id": source_air_id,
            "target_air_id": target_air_id,
        },
        classification=classification,
        ordinal=ordinal,
    )


def _build(*records: AtlasAIRRecord):
    return AtlasContextCompiler()._graph(AtlasAIRPackage(records=records))


def test_graph_builds_stable_node_id_from_air_id() -> None:
    graph, decisions = _build(_record("air-alpha"))

    assert [node.node_id for node in graph.nodes] == ["node-alpha"]
    assert decisions[0].subject_id == "node-alpha"


def test_graph_relationship_has_stable_canonical_representation() -> None:
    records = (
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation("air-relation", "air-alpha", "air-beta", ordinal=2),
    )

    first, _ = _build(*records)
    second, _ = _build(*reversed(records))

    assert canonical_json(first.relationships) == canonical_json(second.relationships)


def test_graph_converts_explicit_relation_candidate() -> None:
    graph, _ = _build(
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation(
            "air-relation",
            "air-alpha",
            "air-beta",
            relationship_type="reports_to",
            ordinal=2,
        ),
    )

    assert len(graph.relationships) == 1
    relationship = graph.relationships[0]
    assert relationship.relationship_type == "reports_to"
    assert relationship.source_node_id == "node-alpha"
    assert relationship.target_node_id == "node-beta"


def test_graph_omits_orphan_relation() -> None:
    graph, _ = _build(
        _record("air-alpha", ordinal=0),
        _relation("air-orphan", "air-alpha", "air-missing", ordinal=1),
    )

    assert graph.relationships == ()


def test_graph_records_orphan_exclusion_decision() -> None:
    graph, decisions = _build(
        _record("air-alpha", ordinal=0),
        _relation("air-orphan", "air-alpha", "air-missing", ordinal=1),
    )

    assert graph.relationships == ()
    orphan = next(item for item in decisions if item.subject_id == "air-orphan")
    assert orphan.stage == AtlasCompilerStage.GRAPH
    assert orphan.action == AtlasSelectionAction.EXCLUDED
    assert orphan.reason_categories == ("orphan_relationship",)
    assert orphan.provider_id == "alpha_provider"


def test_duplicate_relationships_are_canonical_across_input_permutations() -> None:
    alpha = _record("air-alpha", ordinal=0)
    beta = _record("air-beta", ordinal=1)
    first_relation = _relation("air-relation-a", "air-alpha", "air-beta", ordinal=2)
    second_relation = _relation("air-relation-b", "air-alpha", "air-beta", ordinal=3)

    first, _ = _build(alpha, beta, first_relation, second_relation)
    second, _ = _build(second_relation, beta, first_relation, alpha)

    assert len(first.relationships) == 1
    assert canonical_json(first.relationships) == canonical_json(second.relationships)
    assert [item.ordinal for item in first.relationships] == [0]


def test_invalid_explicit_relationship_type_is_rejected() -> None:
    with pytest.raises(ValidationError, match="relationship_type"):
        _build(
            _record("air-alpha", ordinal=0),
            _record("air-beta", ordinal=1),
            _relation(
                "air-relation",
                "air-alpha",
                "air-beta",
                relationship_type="INVALID TYPE",
                ordinal=2,
            ),
        )


def test_graph_propagates_provenance_to_nodes_and_relationships() -> None:
    provenance = _provenance(source_id="source-shared")
    alpha = _record("air-alpha", ordinal=0, provenance=provenance)
    beta = _record("air-beta", ordinal=1)
    relation = _record(
        "air-relation",
        item_type=AtlasAIRItemType.RELATION_CANDIDATE,
        attributes={
            "source_air_id": "air-alpha",
            "target_air_id": "air-beta",
            "relationship_type": "related_to",
        },
        ordinal=2,
        provenance=provenance,
    )

    graph, _ = _build(alpha, beta, relation)

    assert graph.nodes[0].provenance == provenance
    assert graph.relationships[0].provenance == provenance


def test_graph_propagates_classification_to_nodes_and_relationships() -> None:
    alpha = _record(
        "air-alpha",
        ordinal=0,
        classification=AtlasClassification.RESTRICTED,
    )
    beta = _record("air-beta", ordinal=1)
    relation = _relation(
        "air-relation",
        "air-alpha",
        "air-beta",
        ordinal=2,
        classification=AtlasClassification.CONFIDENTIAL,
    )

    graph, _ = _build(alpha, beta, relation)

    assert graph.nodes[0].classification == AtlasClassification.RESTRICTED
    assert graph.relationships[0].classification == AtlasClassification.CONFIDENTIAL


def test_graph_is_cycle_safe_for_explicit_edges() -> None:
    graph, _ = _build(
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation("air-forward", "air-alpha", "air-beta", ordinal=2),
        _relation("air-reverse", "air-beta", "air-alpha", ordinal=3),
    )

    assert {
        (item.source_node_id, item.target_node_id)
        for item in graph.relationships
    } == {("node-alpha", "node-beta"), ("node-beta", "node-alpha")}


def test_graph_nodes_follow_canonical_air_order() -> None:
    graph, _ = _build(
        _record("air-charlie", ordinal=2),
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
    )

    assert [item.node_id for item in graph.nodes] == [
        "node-alpha",
        "node-beta",
        "node-charlie",
    ]
    assert [item.ordinal for item in graph.nodes] == [0, 1, 2]


def test_graph_relationships_follow_canonical_air_order() -> None:
    graph, _ = _build(
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation("air-relation-z", "air-beta", "air-alpha", ordinal=3),
        _relation("air-relation-a", "air-alpha", "air-beta", ordinal=2),
    )

    assert [item.ordinal for item in graph.relationships] == [0, 1]
    assert [
        (item.source_node_id, item.target_node_id)
        for item in graph.relationships
    ] == [("node-alpha", "node-beta"), ("node-beta", "node-alpha")]


def test_graph_output_is_permutation_invariant() -> None:
    records = (
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation("air-relation", "air-alpha", "air-beta", ordinal=2),
    )

    first_graph, first_decisions = _build(*records)
    second_graph, second_decisions = _build(*reversed(records))

    assert first_graph == second_graph
    assert first_decisions == second_decisions


def test_graph_does_not_invent_relationship_from_natural_language() -> None:
    graph, _ = _build(
        _record(
            "air-alpha",
            attributes={"note": "Alpha reports to beta."},
        ),
        _record("air-beta", ordinal=1),
    )

    assert len(graph.nodes) == 2
    assert graph.relationships == ()


def test_relation_candidate_never_becomes_a_context_node() -> None:
    graph, _ = _build(
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation("air-relation", "air-alpha", "air-beta", ordinal=2),
    )

    assert {item.node_id for item in graph.nodes} == {"node-alpha", "node-beta"}
    assert "node-relation" not in graph.source_by_node


def test_graph_never_returns_dangling_relationship_references() -> None:
    graph, _ = _build(
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation("air-valid", "air-alpha", "air-beta", ordinal=2),
        _relation("air-orphan", "air-alpha", "air-missing", ordinal=3),
    )
    node_ids = {item.node_id for item in graph.nodes}

    assert graph.relationships
    assert all(
        item.source_node_id in node_ids and item.target_node_id in node_ids
        for item in graph.relationships
    )
