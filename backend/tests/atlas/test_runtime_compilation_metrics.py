import pytest

from app.atlas.errors import AtlasRuntimeError
from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from .test_compiler_determinism import snapshot
from .test_compiler_validation import _tampered


@pytest.mark.asyncio
async def test_success_metrics_are_bounded_and_complete(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); result = manager.compile_context(snapshot())
    metrics = manager.compilation_metrics.safe_snapshot()
    assert metrics["compilation_attempts"] == metrics["compilation_successes"] == 1
    assert metrics["compilation_failures"] == metrics["active_compilations"] == 0
    assert metrics["peak_active_compilations"] == 1
    assert metrics["last_package_bytes"] == result.context_package.serialized_bytes()
    assert metrics["last_manifest_bytes"] == len(result.manifest.canonical_bytes())
    assert metrics["last_selected_node_count"] == len(result.graph_nodes)
    assert metrics["last_compilation_duration_ms"] >= 0


@pytest.mark.asyncio
async def test_failure_metrics_clear_active_count(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); invalid = _tampered(snapshot())
    with pytest.raises(AtlasRuntimeError): manager.compile_context(invalid)
    metrics = manager.compilation_metrics.safe_snapshot()
    assert metrics["compilation_attempts"] == metrics["compilation_failures"] == 1
    assert metrics["active_compilations"] == 0 and metrics["last_error_category"]


@pytest.mark.asyncio
async def test_metrics_do_not_change_deterministic_output(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize()
    first = manager.compile_context(snapshot()); second = manager.compile_context(snapshot())
    assert first.canonical_bytes() == second.canonical_bytes()
