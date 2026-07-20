import importlib.util
import io
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from email.message import Message


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
                "error_category": None,
                "safe_detail": None,
                "backend_request_id": "request-1",
                "result_type": "generated_answer",
                "cache_pass": "exact_hit",
                "cache_eligible": True,
                "cache_hit": True,
                "cache_hit_type": "exact",
                "cache_similarity_score": None,
                "cache_lookup_duration_ms": 12.5,
                "cache_scope": "global_company",
                "ollama_skipped": True,
                "model_selected": "qwen3:8b",
                "model_role": "operations",
                "model_routing_complexity": "moderate",
                "model_fallback_used": False,
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
                "error_category": "embedding_model_missing",
                "safe_detail": "The configured embedding model is not available.",
                "backend_request_id": "request-2",
                "result_type": "service_failure",
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
    assert "result_type" in paths["csv"].read_text(encoding="utf-8")
    assert "model_selected" in paths["csv"].read_text(encoding="utf-8")
    assert "cache_hit_type" in paths["csv"].read_text(encoding="utf-8")
    assert "exact_hit" in paths["md"].read_text(encoding="utf-8")
    assert "qwen3:8b" in paths["md"].read_text(encoding="utf-8")
    assert "Successful requests: 1/2" in paths["md"].read_text(encoding="utf-8")
    table_lines = [
        line
        for line in paths["md"].read_text(encoding="utf-8").splitlines()
        if line.startswith("|")
    ]
    assert len({line.count("|") for line in table_lines}) == 1


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


def test_run_benchmark_records_run_relative_model_switch_metadata(
    monkeypatch,
    tmp_path,
) -> None:
    benchmark = load_benchmark_module()
    monkeypatch.setattr(
        benchmark,
        "PROMPTS",
        [("one", "One"), ("two", "Two"), ("three", "Three")],
    )
    models = iter(["qwen3:8b", "qwen3:8b", "deepseek-r1:14b"])

    def call_prompt(*_args, **_kwargs):
        return {
            "success": True,
            "error": None,
            "duration_seconds": 1.0,
            "model_selected": next(models),
        }

    monkeypatch.setattr(benchmark, "call_prompt", call_prompt)
    report = benchmark.run_benchmark(
        benchmark.BenchmarkConfig(
            api_root="http://127.0.0.1:8000",
            bearer_token="token",
            timeout_seconds=10,
            output_dir=tmp_path,
            performance_log_path=tmp_path / "performance.jsonl",
        )
    )

    first, second, third = report["results"]
    assert first["case_order"] == 1
    assert first["previous_model"] is None
    assert first["first_request_for_model_in_run"] is True
    assert second["same_model_as_previous_case"] is True
    assert second["model_switch_from_previous_case"] is False
    assert second["first_request_for_model_in_run"] is False
    assert third["previous_model"] == "qwen3:8b"
    assert third["model_switch_from_previous_case"] is True
    assert third["first_request_for_model_in_run"] is True


def test_call_prompt_captures_controlled_backend_error(monkeypatch) -> None:
    benchmark = load_benchmark_module()
    headers = Message()
    headers["X-Request-ID"] = "request-123"
    headers["X-Error-Category"] = "embedding_model_missing"
    body = json.dumps(
        {"detail": "The configured embedding model is not available."}
    ).encode("utf-8")

    def fake_urlopen(*_, **__):
        raise HTTPError(
            url="http://test",
            code=503,
            msg="Service Unavailable",
            hdrs=headers,
            fp=io.BytesIO(body),
        )

    monkeypatch.setattr(benchmark, "urlopen", fake_urlopen)

    result = benchmark.call_prompt(
        "http://127.0.0.1:8000/api/v1",
        "token",
        1,
        "company_policy",
        "What company policy applies?",
    )

    assert result["status_code"] == 503
    assert result["backend_request_id"] == "request-123"
    assert result["error_category"] == "embedding_model_missing"
    assert result["result_type"] == "service_failure"
    assert result["safe_detail"] == "The configured embedding model is not available."


def test_call_prompt_records_connection_reset_instead_of_aborting(monkeypatch) -> None:
    benchmark = load_benchmark_module()

    def reset_connection(*_, **__):
        raise ConnectionResetError("simulated reset")

    monkeypatch.setattr(benchmark, "urlopen", reset_connection)

    result = benchmark.call_prompt(
        "http://127.0.0.1:8000/api/v1",
        "token",
        1,
        "company_policy",
        "What company policy applies?",
    )

    assert result["success"] is False
    assert result["error"] == "ConnectionResetError"
    assert result["result_type"] == "service_failure"


def test_result_type_for_model_errors() -> None:
    benchmark = load_benchmark_module()

    assert benchmark.result_type_for_error("model_inference_timeout") == (
        "inference_timeout"
    )
    assert benchmark.result_type_for_error("model_inference_empty_response") == (
        "empty_model_response"
    )
    assert benchmark.result_type_for_error("model_inference_malformed_response") == (
        "malformed_model_response"
    )
    assert benchmark.result_type_for_error("model_inference_upstream_error") == (
        "upstream_model_error"
    )
    assert benchmark.result_type_for_error("model_inference_truncated") == (
        "truncated_model_response"
    )
