from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.atlas.canonical import FrozenJson, canonical_bytes
from app.atlas.compiler.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import (
    AtlasAIRItemType,
    AtlasAIRRecord,
    AtlasProvenance,
    AtlasScoreBreakdown,
)
from app.atlas.context_package import AtlasContextNode


FIXED_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _candidate(
    suffix: str,
    *,
    provider_id: str = "provider_a",
    total: int = 100,
    priority: int = 0,
    confidence: int = 0,
    freshness_at: datetime | None = FIXED_TIME,
):
    provenance = AtlasProvenance(
        provider_id=provider_id,
        source_id=f"source-{suffix}",
        source_type="fixture",
        source_sequence=0,
        collected_at=FIXED_TIME,
        original_reference=f"reference-{suffix}",
        content_digest=(suffix[0].lower() if suffix[0].lower() in "abcdef0123456789" else "a") * 64,
    )
    record = AtlasAIRRecord(
        air_id=f"air-{suffix}",
        provider_id=provider_id,
        source_reference=f"reference-{suffix}",
        item_type=AtlasAIRItemType.RECORD,
        normalized_title=f"Record {suffix}",
        normalized_content=f"content-{suffix}",
        normalized_attributes=FrozenJson({}),
        confidence_points=confidence,
        freshness_at=freshness_at,
        provenance=provenance,
        ordinal=0,
    )
    node = AtlasContextNode(
        node_id=f"node-{suffix}",
        node_type="record",
        label=f"Record {suffix}",
        provenance=provenance,
    )
    score = AtlasScoreBreakdown(
        provider_priority_points=priority,
        confidence_points=confidence,
        classification_adjustment_points=total - priority - confidence,
        total_score_points=total,
    )
    return node, record, score


def _rank(*candidates):
    return AtlasContextCompiler()._rank(tuple(candidates))


def test_total_score_descending_is_first_tie_break():
    lower = _candidate("a1", total=99, priority=90, confidence=9)
    higher = _candidate("a2", total=100)

    ranked, _ = _rank(lower, higher)

    assert [item.item_id for item in ranked] == ["node-a2", "node-a1"]


def test_provider_priority_descending_breaks_equal_total():
    lower = _candidate("a3", total=100, priority=9)
    higher = _candidate("a4", total=100, priority=10)

    ranked, _ = _rank(lower, higher)

    assert [item.item_id for item in ranked] == ["node-a4", "node-a3"]


def test_confidence_descending_breaks_equal_total_and_priority():
    lower = _candidate("a5", total=100, priority=10, confidence=19)
    higher = _candidate("a6", total=100, priority=10, confidence=20)

    ranked, _ = _rank(lower, higher)

    assert [item.item_id for item in ranked] == ["node-a6", "node-a5"]


def test_freshness_descending_breaks_equal_score_components():
    older = _candidate("a7", freshness_at=FIXED_TIME - timedelta(seconds=1))
    newer = _candidate("a8", freshness_at=FIXED_TIME)

    ranked, _ = _rank(older, newer)

    assert [item.item_id for item in ranked] == ["node-a8", "node-a7"]
    assert ranked[0].freshness_sort_value > ranked[1].freshness_sort_value


def test_provider_id_ascending_breaks_equal_freshness():
    provider_z = _candidate("a9", provider_id="provider_z")
    provider_a = _candidate("b1", provider_id="provider_a")

    ranked, _ = _rank(provider_z, provider_a)

    assert [item.provider_id for item in ranked] == ["provider_a", "provider_z"]


def test_item_id_ascending_is_final_tie_break():
    later = _candidate("b3")
    earlier = _candidate("b2")

    ranked, _ = _rank(later, earlier)

    assert [item.item_id for item in ranked] == ["node-b2", "node-b3"]


def test_ranks_start_at_one_and_are_contiguous():
    candidates = tuple(_candidate(f"c{index}", total=index) for index in range(1, 6))

    ranked, decisions = _rank(*candidates)

    assert [item.deterministic_rank for item in ranked] == [1, 2, 3, 4, 5]
    assert [item.deterministic_rank for item in ranked] == [item.rank for item in decisions]


def test_every_candidate_has_a_total_deterministic_order():
    candidates = (
        _candidate("d1", total=101),
        _candidate("d2", total=100, priority=2),
        _candidate("d3", total=100, priority=1, confidence=3),
        _candidate("d4", total=100, priority=1, confidence=2, freshness_at=FIXED_TIME),
        _candidate("d5", total=100, priority=1, confidence=2, freshness_at=FIXED_TIME - timedelta(seconds=1), provider_id="provider_a"),
        _candidate("d6", total=100, priority=1, confidence=2, freshness_at=FIXED_TIME - timedelta(seconds=1), provider_id="provider_b"),
    )

    ranked, _ = _rank(*reversed(candidates))

    assert [item.item_id for item in ranked] == [candidate[0].node_id for candidate in candidates]


def test_input_permutation_produces_canonical_byte_identical_output():
    candidates = (
        _candidate("e1", total=100),
        _candidate("e2", total=300),
        _candidate("e3", total=200),
    )

    forward = _rank(*candidates)
    reverse = _rank(*reversed(candidates))

    assert canonical_bytes(forward) == canonical_bytes(reverse)


def test_ranking_does_not_mutate_input_sequence_or_models():
    candidates = [
        _candidate("f1", total=1),
        _candidate("f2", total=3),
        _candidate("f3", total=2),
    ]
    before_ids = [id(item) for item in candidates]
    before_bytes = canonical_bytes(candidates)

    _rank(*candidates)

    assert [id(item) for item in candidates] == before_ids
    assert canonical_bytes(candidates) == before_bytes


def test_ranked_item_carries_exact_tie_break_values():
    candidate = _candidate("f4", provider_id="provider_b", total=17, priority=11, confidence=3)

    ranked, decisions = _rank(candidate)

    assert ranked[0].tie_break_values == ("provider_b", "node-f4")
    assert decisions[0].rank == 1
    assert decisions[0].score_points == 17


def test_missing_freshness_sorts_after_timestamped_candidate():
    missing = _candidate("f5", freshness_at=None)
    supplied = _candidate("f6", freshness_at=FIXED_TIME)

    ranked, _ = _rank(missing, supplied)

    assert [item.item_id for item in ranked] == ["node-f6", "node-f5"]
    assert ranked[1].freshness_sort_value == 0
