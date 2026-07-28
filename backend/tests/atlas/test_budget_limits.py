from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest, NexusRetrievalWarning
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_byte_and_token_budgets_trim_context_deterministically() -> None:
    result = NexusRetrievalEngine().retrieve(
        retrieval_snapshot(),
        NexusRetrievalRequest(
            seed_entity_ids=("doc_a",),
            maximum_hops=3,
            maximum_entities=10,
            maximum_relationships=10,
            maximum_bytes=512,
            maximum_tokens_estimate=128,
        ),
    )

    assert result.budget_summary.used_bytes <= 512
    assert result.budget_summary.estimated_tokens <= 128
    assert NexusRetrievalWarning.BYTE_BUDGET_TRIMMED in result.warnings

