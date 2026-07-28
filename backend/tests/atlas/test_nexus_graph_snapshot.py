from pydantic import ValidationError

from app.atlas.providers.nexus import NexusGraphBuilder, NexusGraphSnapshot, NexusEntity


def test_snapshot_is_immutable_and_canonical() -> None:
    snapshot = NexusGraphBuilder.from_graph(
        (NexusEntity(entity_id="ops:task:a", entity_type="task", label="Task A", source_reference="source:a"),),
        (),
    )
    assert isinstance(snapshot, NexusGraphSnapshot)
    assert snapshot.canonical_json() == snapshot.canonical_json()
    try:
        snapshot.entity_count = 10
    except ValidationError:
        pass
    else:
        raise AssertionError("NexusGraphSnapshot must be immutable")
