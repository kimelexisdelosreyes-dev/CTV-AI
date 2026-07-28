from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest
from tests.atlas.nexus_retrieval_fixtures import retrieval_snapshot


def test_retrieval_is_identical_for_100_runs() -> None:
    engine = NexusRetrievalEngine()
    request = NexusRetrievalRequest(seed_entity_ids=("doc_a",), maximum_hops=3, maximum_entities=10, maximum_relationships=10)

    fingerprints = {
        engine.retrieve(retrieval_snapshot(), request).retrieval_fingerprint
        for _ in range(100)
    }

    assert len(fingerprints) == 1

