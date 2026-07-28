from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest, NexusRetrievalWarning
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_budget_optimizer_selects_highest_ranked_items_within_limits() -> None:
    result = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=3, maximum_entities=2, maximum_relationships=1),
    )

    assert len(result.selected_entities) <= 2
    assert len(result.selected_relationships) <= 1
    assert result.selected_entities[0].entity_id == "doc_a"
    assert NexusRetrievalWarning.ENTITY_BUDGET_TRIMMED in result.warnings

