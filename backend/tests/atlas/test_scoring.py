from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_scoring_is_deterministic_and_prefers_priority_relationships() -> None:
    engine = NexusRetrievalEngine()
    first = engine.retrieve(retrieval_snapshot(), NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=1))
    second = engine.retrieve(retrieval_snapshot(), NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=1))

    assert first.retrieval_fingerprint == second.retrieval_fingerprint
    relationship_explanations = [item for item in first.retrieval_explanations if item.item_kind == "relationship"]
    assert relationship_explanations[0].item_id == "rel_doc_policy"
    assert relationship_explanations[0].score >= relationship_explanations[-1].score

