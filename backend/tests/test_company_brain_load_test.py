import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "company_brain_load_test.py"
SPEC = importlib.util.spec_from_file_location("company_brain_load_test", SCRIPT)
assert SPEC and SPEC.loader
load_test = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = load_test
SPEC.loader.exec_module(load_test)


def test_load_summary_reports_required_safe_aggregates() -> None:
    results = [
        load_test.LoadResult(
            True, False, False, True, 20.0, 0.0, 0, "qwen3:8b", "interactive_fast"
        ),
        load_test.LoadResult(
            False, True, False, False, 5.0, 0.0, 20, None, None
        ),
        load_test.LoadResult(
            False, False, True, False, 100.0, 50.0, 3, "deepseek-r1:14b", "interactive_reasoning"
        ),
    ]
    report = load_test.summarize(results, 1.5)
    assert report["total_requests"] == 3
    assert report["success_count"] == 1
    assert report["rejection_count"] == 1
    assert report["timeout_count"] == 1
    assert report["cache_hit_count"] == 1
    assert report["maximum_queue_depth"] == 20
    assert report["throughput_requests_per_second"] == 2.0
    assert report["model_distribution"]["qwen3:8b"] == 1
    assert "prompt" not in str(report).lower()


def test_percentile_is_deterministic() -> None:
    assert load_test.percentile([], 0.95) == 0.0
    assert load_test.percentile([1.0, 2.0, 3.0, 100.0], 0.95) == 100.0
