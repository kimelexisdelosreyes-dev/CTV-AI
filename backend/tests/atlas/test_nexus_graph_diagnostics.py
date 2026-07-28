from app.atlas.providers.nexus import NexusProvider


def test_graph_diagnostics_are_content_free() -> None:
    diagnostics = NexusProvider().metrics.diagnostics()
    serialized = str(diagnostics).lower()
    assert "graph_fingerprint_prefix" in diagnostics
    assert "ctv one" not in serialized
    assert "supports" not in serialized
    assert "source:" not in serialized
