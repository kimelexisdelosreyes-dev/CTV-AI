import pytest

from app.atlas.providers.nexus import NexusEntityInput, NexusGraphImportBatch, NexusProvider
from app.core.config import settings


def test_failed_build_preserves_active_snapshot(monkeypatch) -> None:
    provider = NexusProvider()
    original = provider.graph_store.snapshot
    monkeypatch.setattr(settings, "ctv_one_nexus_max_entities", 0)
    batch = NexusGraphImportBatch(
        source_id="source",
        source_fingerprint="a" * 64,
        entities=(NexusEntityInput(namespace="ops", entity_type="task", external_key="x", label="X", source_reference="source:x"),),
    )

    with pytest.raises(Exception):
        provider.build_and_replace_snapshot((batch,))

    assert provider.graph_store.snapshot is original
    assert provider.metrics.diagnostics()["failed_builds"] == 1
