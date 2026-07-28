import random

from app.atlas.providers.nexus import NexusEntityInput, NexusGraphBuilder, NexusGraphImportBatch


def test_100_import_order_permutations_are_identical() -> None:
    entities = [
        NexusEntityInput(namespace="ops", entity_type="task", external_key=str(index), label=f"Task {index}", source_reference=f"source:{index}")
        for index in range(5)
    ]
    fingerprints = set()
    for seed in range(100):
        shuffled = list(entities)
        random.Random(seed).shuffle(shuffled)
        builder = NexusGraphBuilder()
        builder.add_batch(NexusGraphImportBatch(source_id="source", source_fingerprint="a" * 64, entities=tuple(shuffled)))
        fingerprints.add(builder.build()[0].graph_fingerprint)
    assert len(fingerprints) == 1
