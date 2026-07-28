from __future__ import annotations

from app.atlas.canonical import canonical_json
from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler.compiler import _Graph
from app.atlas.compiler_contracts import (
    AtlasClassification,
    AtlasCompilerStage,
    AtlasSelectionAction,
)

from .test_graph_builder import _record, _relation


def _fact(
    air_id: str,
    value: object,
    *,
    provider_id: str = "alpha_provider",
    subject_key: str = "account",
    predicate: str = "status",
    classification: AtlasClassification = AtlasClassification.INTERNAL,
    ordinal: int = 0,
):
    return _record(
        air_id,
        provider_id=provider_id,
        attributes={
            "predicate": predicate,
            "subject_key": subject_key,
            "value": value,
        },
        classification=classification,
        ordinal=ordinal,
    )


def _graph(*records):
    from app.atlas.compiler_contracts import AtlasAIRPackage

    return AtlasContextCompiler()._graph(AtlasAIRPackage(records=records))[0]


def _conflicts(*records):
    return AtlasContextCompiler()._conflicts(_graph(*records))


def test_structured_fact_conflict_is_detected() -> None:
    conflicts, decisions = _conflicts(
        _fact("air-alpha", "open", ordinal=0),
        _fact("air-beta", "closed", provider_id="beta_provider", ordinal=1),
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "contradictory_fact"
    assert conflicts[0].subject_key == "account"
    assert len(decisions) == 1


def test_explicit_contradiction_relationship_is_detected() -> None:
    graph = _graph(
        _record("air-alpha", ordinal=0),
        _record("air-beta", ordinal=1),
        _relation(
            "air-contradiction",
            "air-alpha",
            "air-beta",
            relationship_type="contradicts",
            ordinal=2,
        ),
    )

    conflicts, decisions = AtlasContextCompiler()._conflicts(graph)

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "explicit_contradiction"
    assert conflicts[0].item_ids == ("node-alpha", "node-beta")
    assert decisions[0].reason_categories == ("conflict_preserved",)


def test_conflict_id_is_deterministic() -> None:
    records = (
        _fact("air-alpha", "open", ordinal=0),
        _fact("air-beta", "closed", provider_id="beta_provider", ordinal=1),
    )

    first, _ = _conflicts(*records)
    second, _ = _conflicts(*records)

    assert first[0].conflict_id == second[0].conflict_id
    assert first[0].conflict_id.startswith("conflict-")


def test_conflict_item_and_provider_ids_are_canonical() -> None:
    conflicts, _ = _conflicts(
        _fact("air-zulu", "open", provider_id="zulu_provider", ordinal=2),
        _fact("air-alpha", "closed", provider_id="alpha_provider", ordinal=0),
        _fact("air-beta", "pending", provider_id="beta_provider", ordinal=1),
    )

    conflict = conflicts[0]
    assert conflict.item_ids == tuple(sorted(conflict.item_ids))
    assert conflict.provider_ids == (
        "alpha_provider",
        "beta_provider",
        "zulu_provider",
    )


def test_conflict_preserves_typed_values() -> None:
    conflicts, _ = _conflicts(
        _fact("air-alpha", 1, ordinal=0),
        _fact("air-beta", 2, provider_id="beta_provider", ordinal=1),
    )

    assert tuple(item.to_python() for item in conflicts[0].values) == (1, 2)


def test_conflict_preserves_all_source_provenance() -> None:
    conflicts, _ = _conflicts(
        _fact("air-alpha", "open", ordinal=0),
        _fact("air-beta", "closed", provider_id="beta_provider", ordinal=1),
    )

    assert [(item.provider_id, item.source_id) for item in conflicts[0].provenance] == [
        ("alpha_provider", "source-air-alpha"),
        ("beta_provider", "source-air-beta"),
    ]


def test_conflict_keeps_most_restrictive_classification_and_remains_open() -> None:
    conflicts, _ = _conflicts(
        _fact(
            "air-alpha",
            "open",
            classification=AtlasClassification.INTERNAL,
            ordinal=0,
        ),
        _fact(
            "air-beta",
            "closed",
            provider_id="beta_provider",
            classification=AtlasClassification.RESTRICTED,
            ordinal=1,
        ),
    )

    conflict = conflicts[0]
    assert conflict.classification == AtlasClassification.RESTRICTED
    assert conflict.status == "open"
    assert conflict.resolution_policy == "preserve"
    assert conflict.selected_item_id is None


def test_equal_structured_values_do_not_create_a_conflict() -> None:
    conflicts, decisions = _conflicts(
        _fact("air-alpha", "open", ordinal=0),
        _fact("air-beta", "open", provider_id="beta_provider", ordinal=1),
    )

    assert conflicts == ()
    assert decisions == ()


def test_prose_only_contradiction_is_not_inferred() -> None:
    conflicts, decisions = _conflicts(
        _record("air-alpha", attributes={"note": "The account is open."}, ordinal=0),
        _record(
            "air-beta",
            provider_id="beta_provider",
            attributes={"note": "The account is not open."},
            ordinal=1,
        ),
    )

    assert conflicts == ()
    assert decisions == ()


def test_conflict_detection_is_permutation_invariant() -> None:
    graph = _graph(
        _fact("air-alpha", "open", ordinal=0),
        _fact("air-beta", "closed", provider_id="beta_provider", ordinal=1),
    )
    permuted = _Graph(
        nodes=tuple(reversed(graph.nodes)),
        relationships=graph.relationships,
        source_by_node=dict(reversed(tuple(graph.source_by_node.items()))),
    )
    compiler = AtlasContextCompiler()

    first_conflicts, first_decisions = compiler._conflicts(graph)
    second_conflicts, second_decisions = compiler._conflicts(permuted)

    assert canonical_json(first_conflicts) == canonical_json(second_conflicts)
    assert canonical_json(first_decisions) == canonical_json(second_decisions)


def test_deduplication_preserves_structured_conflict_candidates() -> None:
    original = _graph(
        _fact("air-alpha", "open", ordinal=0),
        _fact("air-beta", "closed", provider_id="beta_provider", ordinal=1),
    )
    compiler = AtlasContextCompiler()

    optimized, duplicate_decisions = compiler._deduplicate(original)
    conflicts, _ = compiler._conflicts(optimized)

    assert duplicate_decisions == ()
    assert len(conflicts) == 1
    assert conflicts[0].item_ids == ("node-alpha", "node-beta")


def test_conflict_decision_is_safe_and_stage_specific() -> None:
    _, decisions = _conflicts(
        _fact("air-alpha", "open", ordinal=0),
        _fact("air-beta", "closed", provider_id="beta_provider", ordinal=1),
    )

    decision = decisions[0]
    assert decision.stage == AtlasCompilerStage.GRAPH
    assert decision.action == AtlasSelectionAction.SELECTED
    assert decision.reason_categories == ("conflict_preserved",)
    serialized = decision.canonical_json().lower()
    assert "traceback" not in serialized
    assert "exception" not in serialized
