from concurrent.futures import ThreadPoolExecutor

import pytest

from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from .test_compiler_determinism import snapshot
from .test_compiler_validation import _tampered


@pytest.mark.asyncio
async def test_twenty_concurrent_compilations_are_identical_and_balanced(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); source = snapshot()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: manager.compile_context(source), range(20)))
    assert len({item.deterministic_digest for item in results}) == 1
    metrics = manager.compilation_metrics.safe_snapshot()
    assert metrics["compilation_successes"] == 20 and metrics["active_compilations"] == 0
    assert metrics["peak_active_compilations"] <= 4


@pytest.mark.asyncio
async def test_mixed_valid_and_invalid_compilations_are_isolated(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); valid = snapshot(); invalid = _tampered(valid)
    def run(value):
        try: return manager.compile_context(value).status
        except Exception: return "invalid"
    values = [valid] * 10 + [invalid] * 5
    with ThreadPoolExecutor(max_workers=4) as executor: outcomes = list(executor.map(run, values))
    assert outcomes.count("complete") == 10 and outcomes.count("invalid") == 5
    assert manager.compilation_metrics.safe_snapshot()["active_compilations"] == 0
