"""Offline Atlas provider-orchestration benchmark with synthetic providers."""
from __future__ import annotations

import asyncio
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT)); sys.path.insert(0, str(BACKEND_ROOT / "tests"))

from app.atlas.models import AtlasProviderResult
from app.atlas.provider_orchestration import AtlasProviderExecutionPlan
from atlas.provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


async def run(provider_count: int, total_records: int, runs: int = 5):
    per_provider = total_records // provider_count
    providers = [CollectionProvider(f"provider_{index}", result=AtlasProviderResult(provider_id=f"provider_{index}", data={"records":[{"id":f"{index}-{item}", "title":f"Record {item}", "content":"x" * 24} for item in range(per_provider)]})) for index in range(provider_count)]
    manager = runtime_with(*providers); await manager.initialize()
    request = execution_request(*(AtlasProviderExecutionPlan(provider_id=item.definition.provider_id, capabilities=("fixture_context",)) for item in providers))
    totals = []; compiles = []; outcome = None
    for _ in range(runs):
        started = perf_counter(); outcome = await manager.execute_provider_plan(request); totals.append((perf_counter()-started)*1000)
        started = perf_counter(); manager.compile_context(outcome.compilation_snapshot); compiles.append((perf_counter()-started)*1000)
    await manager.shutdown(); assert outcome and outcome.compilation_result
    total_median = median(totals); compile_median = median(compiles)
    return {"runs":runs, "min_ms":round(min(totals),3), "median_ms":round(total_median,3), "max_ms":round(max(totals),3), "compile_median_ms":round(compile_median,3), "orchestration_overhead_ms":round(total_median-compile_median,3), "snapshot_bytes":len(outcome.compilation_snapshot.canonical_bytes()), "package_bytes":outcome.compilation_result.context_package.serialized_bytes(), "manifest_bytes":len(outcome.compilation_result.manifest.canonical_bytes())}


async def main():
    print("small", await run(3, 51)); print("moderate", await run(6, 504))


if __name__ == "__main__": asyncio.run(main())
