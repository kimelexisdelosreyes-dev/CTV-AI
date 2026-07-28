from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_retrieval_deduplicates_entities_relationships_and_paths() -> None:
    result = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(seed_entity_ids=("doc_a", "project_a", "doc_a"), maximum_hops=2, maximum_entities=10, maximum_relationships=10),
    )

    assert len({entity.entity_id for entity in result.selected_entities}) == len(result.selected_entities)
    assert len({relationship.relationship_id for relationship in result.selected_relationships}) == len(result.selected_relationships)
    assert len({path.path_id for path in result.evidence_paths}) == len(result.evidence_paths)

