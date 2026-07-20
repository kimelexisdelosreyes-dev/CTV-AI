import asyncio
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agent_runtime_benchmark.py"
SPEC = importlib.util.spec_from_file_location("agent_runtime_benchmark", SCRIPT)
assert SPEC and SPEC.loader
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def test_all_ten_runtime_benchmark_cases_complete_safely() -> None:
    report = asyncio.run(benchmark.run_runtime_benchmark())
    assert report["case_count"] == 10
    assert report["success_count"] == 10
    required = {
        "selected_agent",
        "agent_version",
        "capability",
        "lifecycle_state",
        "resolution_duration_ms",
        "resolution_fallback",
        "initialization_status",
        "health_status",
        "budget_status",
        "queue_wait_ms",
        "execution_latency_ms",
        "partial_result",
        "fallback_used",
        "success",
    }
    assert all(required.issubset(item) for item in report["results"])

