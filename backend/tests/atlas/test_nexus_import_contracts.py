from pydantic import ValidationError

from app.atlas.providers.nexus import NexusEntityInput, NexusGraphImportBatch


def test_import_contracts_are_immutable_and_fingerprinted() -> None:
    entity = NexusEntityInput(
        namespace="ops",
        entity_type="task",
        external_key="A",
        label="Task A",
        source_reference="source:a",
    )
    batch = NexusGraphImportBatch(
        source_id="source",
        source_fingerprint="a" * 64,
        entities=(entity,),
    )
    assert batch.batch_fingerprint == batch.deterministic_fingerprint()
    try:
        batch.source_id = "changed"
    except ValidationError:
        pass
    else:
        raise AssertionError("NexusGraphImportBatch must be immutable")
