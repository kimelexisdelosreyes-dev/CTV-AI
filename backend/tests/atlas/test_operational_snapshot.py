from pydantic import ValidationError

from app.observability import AtlasObservabilityService, AtlasOperationalSnapshot


def test_operational_snapshot_is_immutable_and_canonical() -> None:
    snapshot = AtlasObservabilityService().snapshot()

    assert isinstance(snapshot, AtlasOperationalSnapshot)
    assert snapshot.canonical_json() == snapshot.canonical_json()
    try:
        snapshot.version = "changed"
    except ValidationError:
        pass
    else:
        raise AssertionError("AtlasOperationalSnapshot must be immutable")
