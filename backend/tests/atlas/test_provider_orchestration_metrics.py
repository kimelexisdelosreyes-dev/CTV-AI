import pytest

from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_metrics_are_bounded_and_outside_snapshot(atlas_settings):
    manager = runtime_with(CollectionProvider()); await manager.initialize(); outcome = await manager.execute_provider_plan(execution_request())
    metrics = manager.provider_orchestrator.metrics.safe_snapshot()
    assert metrics["attempts"] == metrics["successes"] == metrics["provider_calls"] == 1
    assert metrics["active"] == 0 and metrics["last_snapshot_bytes"] == len(outcome.compilation_snapshot.canonical_bytes())
    assert "duration_ms" not in outcome.compilation_snapshot.canonical_json()
