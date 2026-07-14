from app.schemas.context import ContextMetadata


def test_context_metadata_defaults_to_disabled() -> None:
    metadata = ContextMetadata()
    assert metadata.applied is False
    assert metadata.skills_used == []
    assert metadata.tools_used == []
    assert metadata.memories_used == 0
