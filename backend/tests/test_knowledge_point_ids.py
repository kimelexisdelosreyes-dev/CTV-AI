import uuid

def test_deterministic_qdrant_point_ids_are_uuid() -> None:
    document_id = uuid.uuid4()
    first = uuid.uuid5(document_id, "chunk-1")
    second = uuid.uuid5(document_id, "chunk-1")
    assert first == second
    assert isinstance(first, uuid.UUID)
