from __future__ import annotations

import statistics
from pathlib import Path
import sys
from time import perf_counter

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "tests"))

from app.forge.context_adapter import ForgeContextAdapter, estimate_text_tokens
from app.forge.prompt_builder import integrate_atlas_context
from forge.conftest import make_package


def milliseconds(started: float) -> float:
    return (perf_counter() - started) * 1000


def benchmark(*, nodes: int, iterations: int = 100) -> dict[str, float | int]:
    package = make_package(node_count=nodes, content_chars=160)
    adapter = ForgeContextAdapter(token_budget=32_000, atlas_enabled=True, adapter_enabled=True)
    base_prompt = "System\nrules\n\nConversation\nrequest\n\nCompany Brain\nfacts\n\nMemory\nprior"
    validation: list[float] = []
    estimation: list[float] = []
    conversion: list[float] = []
    prompt: list[float] = []
    total: list[float] = []
    tokens = 0
    for _ in range(iterations):
        started = perf_counter()
        adapter._validate_package(package)
        validation.append(milliseconds(started))
        started = perf_counter()
        sum(estimate_text_tokens(item.excerpt) for item in package.evidence)
        estimation.append(milliseconds(started))
        started = perf_counter()
        window = adapter.adapt(package)
        adapter_ms = milliseconds(started)
        conversion.append(max(adapter_ms - validation[-1], 0.0))
        tokens = window.estimated_tokens
        started = perf_counter()
        integrate_atlas_context(
            base_prompt,
            window,
            atlas_enabled=True,
            forge_adapter_enabled=True,
        )
        prompt.append(milliseconds(started))
        total.append(adapter_ms + prompt[-1])
    return {
        "nodes": nodes,
        "iterations": iterations,
        "estimated_tokens": tokens,
        "package_validation_median_ms": round(statistics.median(validation), 3),
        "token_estimation_median_ms": round(statistics.median(estimation), 3),
        "context_conversion_median_ms": round(statistics.median(conversion), 3),
        "prompt_integration_median_ms": round(statistics.median(prompt), 3),
        "total_min_ms": round(min(total), 3),
        "total_median_ms": round(statistics.median(total), 3),
        "total_max_ms": round(max(total), 3),
    }


if __name__ == "__main__":
    for size in (16, 64):
        result = benchmark(nodes=size)
        print(" ".join(f"{key}={value}" for key, value in result.items()))
