import pytest

from app.atlas.providers.nexus import NexusGraphInfrastructureError, NexusGraphSchemaVersion


def test_supported_schema_version_accepted() -> None:
    version = NexusGraphSchemaVersion.parse("1.0")
    version.ensure_supported()
    assert version.value == "1.0"


def test_unsupported_schema_version_rejected() -> None:
    with pytest.raises(NexusGraphInfrastructureError):
        NexusGraphSchemaVersion.parse("2.0").ensure_supported()
