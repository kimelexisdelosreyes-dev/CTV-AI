from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 420
DEFAULT_OUTPUT_DIR = Path("benchmarks") / "reports"
DEFAULT_PERFORMANCE_LOG_PATH = Path("logs") / "performance.jsonl"
ENDPOINT_PATH = "/api/v1/knowledge/ask"

PROMPTS = [
    (
        "operations_priorities",
        "What are the highest operational priorities for the company today?",
    ),
    (
        "overdue_tasks",
        "Which tasks are overdue, and what should be handled first?",
    ),
    (
        "company_policy",
        "What company policy should I follow for time off or leave requests?",
    ),
    (
        "equipment_manual",
        "What setup steps should I follow from the approved equipment manuals?",
    ),
    (
        "production_sop",
        "Summarize the approved production SOP for preparing a shoot.",
    ),
    (
        "technical_troubleshooting",
        "How should I troubleshoot a technical issue with production equipment?",
    ),
    (
        "brand_guidance",
        "What brand guidance should I follow when preparing client-facing material?",
    ),
    (
        "mixed_operations_plus_knowledge",
        "Combine current operations priorities with relevant approved knowledge guidance.",
    ),
    (
        "employee_context_question",
        "Based on my role and preferences, what should I focus on next?",
    ),
    (
        "repeat_operations_priorities",
        "What are the highest operational priorities for the company today?",
    ),
]


@dataclass(frozen=True)
class BenchmarkConfig:
    api_root: str
    bearer_token: str
    timeout_seconds: float
    output_dir: Path
    performance_log_path: Path


def config_from_env() -> BenchmarkConfig:
    api_root = (
        os.getenv("CTV_ONE_API_ROOT")
        or os.getenv("API_ROOT")
        or ""
    ).rstrip("/")
    bearer_token = (
        os.getenv("CTV_ONE_BEARER_TOKEN")
        or os.getenv("BEARER_TOKEN")
        or ""
    )
    output_dir = Path(os.getenv("CTV_ONE_BENCHMARK_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
    performance_log_path = Path(
        os.getenv(
            "CTV_ONE_PERFORMANCE_LOG_PATH",
            str(DEFAULT_PERFORMANCE_LOG_PATH),
        )
    )

    timeout_value = os.getenv("CTV_ONE_BENCHMARK_TIMEOUT_SECONDS", "")
    timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    if timeout_value:
        try:
            timeout_seconds = float(timeout_value)
        except ValueError as exc:
            raise ValueError(
                "CTV_ONE_BENCHMARK_TIMEOUT_SECONDS must be a number."
            ) from exc

    if not api_root:
        raise ValueError("Set CTV_ONE_API_ROOT to the API root, for example http://127.0.0.1:8000.")
    if not bearer_token:
        raise ValueError("Set CTV_ONE_BEARER_TOKEN to a valid bearer token.")
    if timeout_seconds <= 0:
        raise ValueError("CTV_ONE_BENCHMARK_TIMEOUT_SECONDS must be greater than zero.")

    return BenchmarkConfig(
        api_root=api_root,
        bearer_token=bearer_token,
        timeout_seconds=timeout_seconds,
        output_dir=output_dir,
        performance_log_path=performance_log_path,
    )


def benchmark_url(api_root: str) -> str:
    if api_root.endswith(ENDPOINT_PATH):
        return api_root
    if api_root.endswith("/api/v1"):
        return f"{api_root}/knowledge/ask"
    return f"{api_root}{ENDPOINT_PATH}"


def call_prompt(
    api_root: str,
    bearer_token: str,
    timeout_seconds: float,
    case_label: str,
    question: str,
    performance_log_path: Path = DEFAULT_PERFORMANCE_LOG_PATH,
) -> dict[str, Any]:
    payload = {
        "question": question,
        "top_k": 5,
        "assistant": "general",
        "use_employee_context": True,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        benchmark_url(api_root),
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    started_at = perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body) if response_body else {}
            status_code = response.status
            headers = response.headers
            ok = 200 <= status_code < 300
            error = None
    except HTTPError as exc:
        status_code = exc.code
        headers = exc.headers
        response_body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(response_body) if response_body else {}
        except json.JSONDecodeError:
            data = {}
        ok = False
        error = f"HTTP {exc.code}"
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        status_code = None
        headers = {}
        data = {}
        ok = False
        error = type(exc).__name__

    duration_seconds = round(perf_counter() - started_at, 3)
    answer = data.get("answer") if isinstance(data, dict) else None
    sources = data.get("sources") if isinstance(data, dict) else None
    personalization = data.get("personalization") if isinstance(data, dict) else None
    detail = data.get("detail") if isinstance(data, dict) else None
    backend_request_id = headers.get("X-Request-ID") if headers else None
    error_category = headers.get("X-Error-Category") if headers else None
    result_type = headers.get("X-Result-Type") if headers else None
    if not ok:
        result_type = result_type_for_error(error_category)
    elif not result_type:
        result_type = (
            "no_knowledge_fallback"
            if answer == "I could not find relevant approved company knowledge for this request."
            else "generated_answer"
        )

    performance_event = read_performance_event(
        backend_request_id or "",
        performance_log_path,
    )
    prompt_metrics = prompt_metrics_from_event(performance_event)

    return {
        "case_label": case_label,
        "success": ok,
        "status_code": status_code,
        "duration_seconds": duration_seconds,
        "error": error,
        "error_category": error_category,
        "safe_detail": detail if isinstance(detail, str) else None,
        "backend_request_id": backend_request_id,
        "result_type": result_type,
        "answer_chars": len(answer) if isinstance(answer, str) else 0,
        "source_count": len(sources) if isinstance(sources, list) else 0,
        "operational_context_applied": (
            personalization.get("operational_context_applied")
            if isinstance(personalization, dict)
            else None
        ),
        "operational_tasks_used": (
            personalization.get("operational_tasks_used")
            if isinstance(personalization, dict)
            else None
        ),
        **prompt_metrics,
    }


def run_benchmark(config: BenchmarkConfig) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    for index, (case_label, question) in enumerate(PROMPTS, 1):
        print(f"[{index}/{len(PROMPTS)}] {case_label}")
        result = call_prompt(
            config.api_root,
            config.bearer_token,
            config.timeout_seconds,
            case_label,
            question,
            config.performance_log_path,
        )
        results.append(result)
        status = "ok" if result["success"] else f"failed ({result['error']})"
        print(f"  {status} in {result['duration_seconds']}s")

    return {
        "event": "company_brain_baseline_benchmark",
        "generated_at": generated_at,
        "api_root": config.api_root,
        "timeout_seconds": config.timeout_seconds,
        "prompt_count": len(PROMPTS),
        "results": results,
    }


def result_type_for_error(error_category: str | None) -> str:
    return {
        "model_inference_timeout": "inference_timeout",
        "model_inference_empty_response": "empty_model_response",
        "model_inference_truncated": "truncated_model_response",
        "model_inference_malformed_response": "malformed_model_response",
        "model_inference_upstream_error": "upstream_model_error",
    }.get(error_category or "", "service_failure")


def read_performance_event(
    request_id: str,
    log_path: Path,
) -> dict[str, Any] | None:
    if not request_id or not log_path.exists():
        return None

    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("request_id") == request_id:
            return event
    return None


def prompt_metrics_from_event(event: dict[str, Any] | None) -> dict[str, Any]:
    metrics = event.get("metrics") if isinstance(event, dict) else {}
    requirements = event.get("context_requirements") if isinstance(event, dict) else {}
    stages = event.get("stages") if isinstance(event, dict) else {}
    if not isinstance(metrics, dict):
        metrics = {}
    if not isinstance(requirements, dict):
        requirements = {}
    if not isinstance(stages, dict):
        stages = {}

    return {
        "selected_context_types": requirements.get("selected_context_types", []),
        "parallel_retrieval_used": metrics.get("retrieval_parallel_used"),
        "knowledge_retrieval_duration_ms": metrics.get(
            "knowledge_retrieval_duration_ms"
        ),
        "operations_retrieval_duration_ms": metrics.get(
            "operations_retrieval_duration_ms"
        ),
        "operations_context_source": metrics.get("operations_context_source"),
        "operations_snapshot_age_seconds": metrics.get(
            "operations_snapshot_age_seconds"
        ),
        "operations_snapshot_freshness": metrics.get(
            "operations_snapshot_freshness"
        ),
        "operations_snapshot_task_count": metrics.get(
            "operations_snapshot_task_count"
        ),
        "employee_retrieval_duration_ms": metrics.get(
            "employee_retrieval_duration_ms"
        ),
        "history_retrieval_duration_ms": metrics.get(
            "history_retrieval_duration_ms"
        ),
        "retrieval_total_duration_ms": metrics.get("retrieval_total_duration_ms"),
        "prompt_assembly_duration_ms": seconds_to_ms(stages.get("prompt_builder")),
        "inference_duration_ms": seconds_to_ms(stages.get("ollama_total")),
        "sequential_estimated_duration_ms": metrics.get(
            "sequential_estimated_duration_ms"
        ),
        "parallel_time_saved_estimate_ms": metrics.get(
            "parallel_time_saved_estimate_ms"
        ),
        "context_degraded": metrics.get("context_degraded"),
        "successful_context_components": metrics.get(
            "successful_context_components",
            [],
        ),
        "failed_context_components": metrics.get("failed_context_components", []),
        "timed_out_context_components": metrics.get(
            "timed_out_context_components",
            [],
        ),
        "final_prompt_chars": metrics.get("final_prompt_chars"),
        "estimated_prompt_tokens": metrics.get("estimated_prompt_tokens"),
        "knowledge_chunks_used": metrics.get("knowledge_chunks_final"),
        "operational_tasks_selected": metrics.get("operational_tasks_final"),
        "employee_context_included": requirements.get("include_employee"),
        "prompt_budget_applied": bool(metrics.get("prompt_budget_applied")),
        "prompt_components_omitted": metrics.get("prompt_components_omitted", []),
        "prompt_components_truncated": metrics.get("prompt_components_truncated", []),
    }


def seconds_to_ms(value: Any) -> float | None:
    if isinstance(value, int | float):
        return round(float(value) * 1000, 3)
    return None


def report_paths(output_dir: Path, generated_at: str) -> dict[str, Path]:
    stamp = generated_at.replace(":", "").replace("+", "Z")
    return {
        "json": output_dir / f"company-brain-baseline-{stamp}.json",
        "csv": output_dir / f"company-brain-baseline-{stamp}.csv",
        "md": output_dir / f"company-brain-baseline-{stamp}.md",
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = report_paths(output_dir, str(report["generated_at"]))
    results = report.get("results", [])

    paths["json"].write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with paths["csv"].open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "case_label",
            "success",
            "status_code",
            "duration_seconds",
            "error",
            "error_category",
            "safe_detail",
            "backend_request_id",
            "result_type",
            "selected_context_types",
            "parallel_retrieval_used",
            "knowledge_retrieval_duration_ms",
            "operations_retrieval_duration_ms",
            "operations_context_source",
            "operations_snapshot_age_seconds",
            "operations_snapshot_freshness",
            "operations_snapshot_task_count",
            "employee_retrieval_duration_ms",
            "history_retrieval_duration_ms",
            "retrieval_total_duration_ms",
            "prompt_assembly_duration_ms",
            "inference_duration_ms",
            "sequential_estimated_duration_ms",
            "parallel_time_saved_estimate_ms",
            "context_degraded",
            "successful_context_components",
            "failed_context_components",
            "timed_out_context_components",
            "final_prompt_chars",
            "estimated_prompt_tokens",
            "knowledge_chunks_used",
            "operational_tasks_selected",
            "employee_context_included",
            "prompt_budget_applied",
            "prompt_components_omitted",
            "prompt_components_truncated",
            "answer_chars",
            "source_count",
            "operational_context_applied",
            "operational_tasks_used",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({field: result.get(field) for field in fieldnames})

    successful = sum(1 for result in results if result.get("success"))
    lines = [
        "# Company Brain Baseline Benchmark",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- API root: {report['api_root']}",
        f"- Timeout seconds: {report['timeout_seconds']}",
        f"- Successful requests: {successful}/{len(results)}",
        "",
        "| Case | Result | Context | Prompt chars | Tokens | Budget | "
        "Parallel | Retrieval ms | Ops source | Snapshot age | Freshness | Saved est. ms | Degraded | Success | Status | "
        "Seconds | Sources | Ops tasks | Error |",
        "| --- | --- | --- | ---: | ---: | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | "
        "---: | ---: | ---: | --- |",
    ]
    for result in results:
        lines.append(
            "| {case_label} | {result_type} | {context} | {prompt_chars} | "
            "{tokens} | {budget} | {parallel} | {retrieval_ms} | {ops_source} | "
            "{snapshot_age} | {freshness} | {saved_ms} | {degraded} | {success} | {status_code} | "
            "{duration_seconds} | {source_count} | {operational_tasks_used} | "
            "{error} |".format(
                case_label=result.get("case_label"),
                result_type=result.get("result_type") or "",
                context=",".join(result.get("selected_context_types") or []),
                prompt_chars=result.get("final_prompt_chars") or "",
                tokens=result.get("estimated_prompt_tokens") or "",
                budget=result.get("prompt_budget_applied") or False,
                parallel=result.get("parallel_retrieval_used"),
                retrieval_ms=result.get("retrieval_total_duration_ms") or "",
                ops_source=result.get("operations_context_source") or "",
                snapshot_age=result.get("operations_snapshot_age_seconds") or "",
                freshness=result.get("operations_snapshot_freshness") or "",
                saved_ms=result.get("parallel_time_saved_estimate_ms") or "",
                degraded=result.get("context_degraded"),
                success=result.get("success"),
                status_code=result.get("status_code") or "",
                duration_seconds=result.get("duration_seconds"),
                source_count=result.get("source_count"),
                operational_tasks_used=result.get("operational_tasks_used"),
                error=result.get("error") or "",
            )
        )
    paths["md"].write_text("\n".join(lines) + "\n", encoding="utf-8")

    return paths


def main() -> int:
    try:
        config = config_from_env()
    except ValueError as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        return 2

    report = run_benchmark(config)
    paths = write_reports(report, config.output_dir)
    print("Reports written:")
    for path in paths.values():
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
