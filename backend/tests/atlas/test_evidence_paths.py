from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_evidence_paths_are_deterministic_and_explain_selection_without_ai() -> None:
    result = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=2, maximum_entities=10, maximum_relationships=10),
    )

    assert result.evidence_paths
    assert all(path.explanation.startswith(("entity_priority:", "relationship_priority:")) for path in result.evidence_paths)
    assert "llm" not in result.canonical_json().lower()
    assert "embedding" not in result.canonical_json().lower()

