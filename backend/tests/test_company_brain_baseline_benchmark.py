import importlib.util
import sys
from pathlib import Path


def load_benchmark_module():
    script_path = None
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "scripts" / "company_brain_baseline.py"
        if candidate.exists():
            script_path = candidate
            break
    assert script_path is not None
    spec = importlib.util.spec_from_file_location(
        "company_brain_baseline",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_benchmark_report_generation_writes_json_csv_and_markdown(tmp_path) -> None:
    benchmark = load_benchmark_module()
    report = {
        "event": "company_brain_baseline_benchmark",
        "generated_at": "2026-07-17T00:00:00+00:00",
        "api_root": "http://127.0.0.1:8000",
        "timeout_seconds": 420,
        "prompt_count": 2,
        "results": [
            {
                "case_label": "operations_priorities",
                "success": True,
                "status_code": 200,
                "duration_seconds": 1.25,
                "error": None,
                "answer_chars": 120,
                "source_count": 2,
                "operational_context_applied": True,
                "operational_tasks_used": 3,
            },
            {
                "case_label": "overdue_tasks",
                "success": False,
                "status_code": 500,
                "duration_seconds": 0.5,
                "error": "HTTP 500",
                "answer_chars": 0,
                "source_count": 0,
                "operational_context_applied": None,
                "operational_tasks_used": None,
            },
        ],
    }

    paths = benchmark.write_reports(report, tmp_path)

    assert set(paths) == {"json", "csv", "md"}
    assert paths["json"].exists()
    assert paths["csv"].exists()
    assert paths["md"].exists()
    assert "CTV_ONE_BEARER_TOKEN" not in paths["json"].read_text(encoding="utf-8")
    assert "operations_priorities" in paths["csv"].read_text(encoding="utf-8")
    assert "Successful requests: 1/2" in paths["md"].read_text(encoding="utf-8")


def test_benchmark_url_accepts_api_root_or_full_endpoint() -> None:
    benchmark = load_benchmark_module()

    assert benchmark.benchmark_url("http://127.0.0.1:8000") == (
        "http://127.0.0.1:8000/api/v1/knowledge/ask"
    )
    assert benchmark.benchmark_url("http://127.0.0.1:8000/api/v1") == (
        "http://127.0.0.1:8000/api/v1/knowledge/ask"
    )
    assert benchmark.benchmark_url("http://127.0.0.1:8000/api/v1/knowledge/ask") == (
        "http://127.0.0.1:8000/api/v1/knowledge/ask"
    )
