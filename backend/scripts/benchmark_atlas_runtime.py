"""Offline runtime-manager overhead benchmark for Atlas compilation."""
from __future__ import annotations

import asyncio
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "tests"))

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from atlas.test_compiler_determinism import snapshot


async def benchmark(runs: int = 10) -> dict[str, object]:
    source = snapshot(records=84, providers=6)
    compiler = AtlasContextCompiler()
    manager = AtlasRuntimeManager(AtlasProviderRegistry(), compiler=compiler)
    await manager.initialize()
    direct_ms = []
    runtime_ms = []
    result = None
    for _ in range(runs):
        started = perf_counter(); compiler.compile(source); direct_ms.append((perf_counter() - started) * 1000)
        started = perf_counter(); result = manager.compile_context(source); runtime_ms.append((perf_counter() - started) * 1000)
    await manager.shutdown()
    assert result is not None
    direct = median(direct_ms); runtime = median(runtime_ms)
    return {
        "runs": runs,
        "direct_median_ms": round(direct, 3),
        "runtime_median_ms": round(runtime, 3),
        "overhead_ms": round(runtime - direct, 3),
        "overhead_percent": round(((runtime - direct) / direct) * 100, 3),
        "package_bytes": result.context_package.serialized_bytes(),
        "manifest_bytes": len(result.manifest.canonical_bytes()),
    }


if __name__ == "__main__":
    print(asyncio.run(benchmark()))
