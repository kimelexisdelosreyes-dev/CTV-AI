from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_retrieval_engine_selects_seed_and_neighbors() -> None:
    result = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=1, maximum_entities=4, maximum_relationships=4),
    )

    assert [entity.entity_id for entity in result.selected_entities] == ["doc_a", "event_a", "policy_a", "project_a"]
    assert {relationship.relationship_id for relationship in result.selected_relationships} == {
        "rel_doc_policy",
        "rel_doc_project",
        "rel_event_doc",
    }
    assert result.graph_fingerprint == retrieval_snapshot().graph_fingerprint
    assert result.retrieval_fingerprint == result.computed_fingerprint()

