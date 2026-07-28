"""Offline deterministic Atlas compiler benchmark; requires no services."""
from __future__ import annotations

from statistics import median
from time import perf_counter
from pathlib import Path
import sys

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_ROOT))
sys.path.insert(0, str(_BACKEND_ROOT / "tests"))
from atlas.test_compiler_determinism import snapshot
from app.atlas.compiler import AtlasContextCompiler


def run(records: int, providers: int, runs: int = 5) -> dict[str, object]:
    source = snapshot(records=records, providers=providers)
    values = []
    result = None
    for _ in range(runs):
        start = perf_counter(); result = AtlasContextCompiler().compile(source); values.append((perf_counter() - start) * 1000)
    assert result is not None
    return {"runs": runs, "min_ms": round(min(values), 3), "median_ms": round(median(values), 3), "max_ms": round(max(values), 3), "package_bytes": result.context_package.serialized_bytes(), "manifest_bytes": len(result.manifest.canonical_bytes()), "nodes": len(result.graph_nodes), "decisions": len(result.manifest.entries), "digest": result.deterministic_digest}


if __name__ == "__main__":
    print("small", run(25, 2)); print("moderate", run(84, 6))
