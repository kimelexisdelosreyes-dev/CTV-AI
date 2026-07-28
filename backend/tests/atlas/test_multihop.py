from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_multihop_caps_at_three_and_handles_cycles() -> None:
    result = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=3, maximum_entities=10, maximum_relationships=10),
    )

    assert max(path.hop_count for path in result.evidence_paths) <= 3
    assert len({entity.entity_id for entity in result.selected_entities}) == len(result.selected_entities)
    assert len(result.selected_entities) == 5


def test_zero_hop_returns_seed_only() -> None:
    result = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=0, maximum_entities=10, maximum_relationships=10),
    )

    assert [entity.entity_id for entity in result.selected_entities] == ["doc_a"]
    assert result.selected_relationships == ()

