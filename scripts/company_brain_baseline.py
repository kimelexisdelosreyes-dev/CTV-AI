from __future__ import annotations

import csv
import asyncio
import importlib.util
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
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "benchmarks" / "reports"
DEFAULT_PERFORMANCE_LOG_PATH = REPO_ROOT / "logs" / "performance.jsonl"
ENDPOINT_PATH = "/api/v1/knowledge/ask"
STREAM_ENDPOINT_PATH = "/api/v1/knowledge/ask/stream"

BASELINE_PROMPTS = [
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

SUPERVISOR_PROMPTS = [
    ("supervisor_direct_knowledge", "What company policy applies to leave requests?"),
    ("supervisor_direct_operations", "What tasks are overdue right now?"),
    (
        "supervisor_operations_plus_knowledge",
        "Compare current overdue production tasks with our approved production policy.",
    ),
    (
        "supervisor_employee_plus_operations",
        "Review my responsibilities against current operations priorities.",
    ),
    (
        "supervisor_operations_plus_recommendation",
        "Review current operations priorities and recommend the safest next actions.",
    ),
    (
        "supervisor_three_agent_executive_summary",
        "Prepare an executive summary using current operations, approved policy, and recommendations.",
    ),
    (
        "supervisor_planner_fallback",
        "Prepare a bounded management brief from approved enterprise information.",
    ),
    (
        "supervisor_optional_partial_failure",
        "Summarize current operations and add any available supporting policy guidance.",
    ),
    (
        "supervisor_streaming",
        "Compare current priorities with approved guidance and provide a concise brief.",
    ),
    (
        "supervisor_direct_cache_hit_under_load",
        "What company policy applies to leave requests?",
    ),
]

PROMPTS = BASELINE_PROMPTS + SUPERVISOR_PROMPTS
SUPERVISOR_CASE_MODES = {
    "supervisor_direct_knowledge": "direct",
    "supervisor_direct_operations": "direct",
    "supervisor_direct_cache_hit_under_load": "direct",
    **{
        label: "supervised"
        for label, _ in SUPERVISOR_PROMPTS
        if label not in {
            "supervisor_direct_knowledge",
            "supervisor_direct_operations",
            "supervisor_direct_cache_hit_under_load",
        }
    },
}
SUPERVISOR_CASE_MODES["supervisor_planner_fallback"] = "direct"
BENCHMARK_LOCAL_FAILURE_INJECTIONS = {
    "supervisor_planner_fallback": "planner_failure",
}

PARAPHRASES = {
    "operations_priorities": "Which company operations need the most attention today?",
    "overdue_tasks": "What overdue work should be addressed first?",
    "company_policy": "Which approved leave policy applies when requesting time off?",
    "equipment_manual": "According to the approved manuals, how should the equipment be set up?",
    "production_sop": "What does the approved SOP require before a production shoot?",
    "technical_troubleshooting": "What approved steps apply when production equipment has a technical problem?",
    "brand_guidance": "Which approved brand rules apply to client-facing materials?",
    "mixed_operations_plus_knowledge": "Relate today's operations priorities to the relevant approved guidance.",
    "employee_context_question": "Given my role and preferences, what deserves my attention next?",
    "repeat_operations_priorities": "Which company operations need the most attention today?",
    "supervisor_direct_knowledge": "Which approved leave policy should I follow?",
    "supervisor_direct_operations": "Which work items are currently overdue?",
    "supervisor_operations_plus_knowledge": "Relate overdue production work to the approved production policy.",
    "supervisor_employee_plus_operations": "How do my responsibilities align with today's operations priorities?",
    "supervisor_operations_plus_recommendation": "Recommend next steps based on current operational priorities.",
    "supervisor_three_agent_executive_summary": "Create a management summary from operations, approved policy, and recommendations.",
    "supervisor_planner_fallback": "Create a safe management brief from available approved enterprise context.",
    "supervisor_optional_partial_failure": "Summarize operations with any available policy support.",
    "supervisor_streaming": "Briefly compare current priorities and approved guidance.",
    "supervisor_direct_cache_hit_under_load": "Which approved leave policy should I follow?",
}


@dataclass(frozen=True)
class BenchmarkConfig:
    api_root: str
    bearer_token: str
    timeout_seconds: float
    output_dir: Path
    performance_log_path: Path
    cache_passes: bool = False


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
        cache_passes=os.getenv("CTV_ONE_BENCHMARK_CACHE_PASSES", "").lower()
        in {"1", "true", "yes", "on"},
    )


def benchmark_url(api_root: str) -> str:
    if api_root.endswith(ENDPOINT_PATH):
        return api_root
    if api_root.endswith("/api/v1"):
        return f"{api_root}/knowledge/ask"
    return f"{api_root}{ENDPOINT_PATH}"


def stream_benchmark_url(api_root: str) -> str:
    ask_url = benchmark_url(api_root)
    return ask_url.removesuffix(ENDPOINT_PATH) + STREAM_ENDPOINT_PATH


def stream_start_request_id(response_body: str) -> str | None:
    event_name = ""
    for line in response_body.splitlines():
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ").strip()
        elif event_name == "start" and line.startswith("data: "):
            try:
                payload = json.loads(line.removeprefix("data: "))
            except json.JSONDecodeError:
                return None
            request_id = payload.get("request_id") if isinstance(payload, dict) else None
            return request_id if isinstance(request_id, str) else None
    return None


def call_prompt(
    api_root: str,
    bearer_token: str,
    timeout_seconds: float,
    case_label: str,
    question: str,
    performance_log_path: Path = DEFAULT_PERFORMANCE_LOG_PATH,
    *,
    supervisor_mode: str = "auto",
    streaming: bool = False,
) -> dict[str, Any]:
    payload = {
        "question": question,
        "top_k": 5,
        "assistant": "general",
        "use_employee_context": True,
        "supervisor_mode": supervisor_mode,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        stream_benchmark_url(api_root) if streaming else benchmark_url(api_root),
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    started_at = perf_counter()
    streamed_request_id = None
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            data = (
                {}
                if streaming
                else json.loads(response_body) if response_body else {}
            )
            status_code = response.status
            headers = response.headers
            ok = 200 <= status_code < 300 and (
                not streaming or "event: done" in response_body
            )
            if streaming:
                streamed_request_id = stream_start_request_id(response_body)
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
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
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
    backend_request_id = (
        headers.get("X-Request-ID") if headers else None
    ) or streamed_request_id
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
    previous_model: str | None = None
    seen_models: set[str] = set()

    passes = [("cold_cache", PROMPTS)]
    if config.cache_passes:
        passes.extend(
            [
                ("exact_hit", PROMPTS),
                (
                    "semantic_hit",
                    [(label, PARAPHRASES[label]) for label, _ in PROMPTS],
                ),
            ]
        )
    cases = [
        (pass_name, label, question)
        for pass_name, prompts in passes
        for label, question in prompts
    ]

    for index, (pass_name, case_label, question) in enumerate(cases, 1):
        print(f"[{index}/{len(cases)}] {pass_name}: {case_label}")
        result = call_prompt(
            config.api_root,
            config.bearer_token,
            config.timeout_seconds,
            case_label,
            question,
            config.performance_log_path,
            supervisor_mode=SUPERVISOR_CASE_MODES.get(case_label, "auto"),
            streaming=case_label == "supervisor_streaming",
        )
        result["benchmark_failure_injection"] = BENCHMARK_LOCAL_FAILURE_INJECTIONS.get(
            case_label
        )
        selected_model = result.get("model_selected")
        model_known = isinstance(selected_model, str) and bool(selected_model)
        previous_known = isinstance(previous_model, str) and bool(previous_model)
        result.update(
            {
                "case_order": index,
                "cache_pass": pass_name,
                "previous_model": previous_model,
                "same_model_as_previous_case": (
                    selected_model == previous_model
                    if model_known and previous_known
                    else None
                ),
                "model_switch_from_previous_case": (
                    selected_model != previous_model
                    if model_known and previous_known
                    else None
                ),
                "first_request_for_model_in_run": (
                    selected_model not in seen_models if model_known else None
                ),
            }
        )
        if model_known:
            seen_models.add(selected_model)
            previous_model = selected_model
        results.append(result)
        status = "ok" if result["success"] else f"failed ({result['error']})"
        print(f"  {status} in {result['duration_seconds']}s")

    runtime_report = run_agent_runtime_cases()
    return {
        "event": "company_brain_baseline_benchmark",
        "generated_at": generated_at,
        "api_root": config.api_root,
        "timeout_seconds": config.timeout_seconds,
        "prompt_count": len(PROMPTS),
        "baseline_prompt_count": len(BASELINE_PROMPTS),
        "supervisor_prompt_count": len(SUPERVISOR_PROMPTS),
        "request_count": len(cases),
        "cache_passes_enabled": config.cache_passes,
        "results": results,
        "agent_runtime_case_count": runtime_report["case_count"],
        "agent_runtime_success_count": runtime_report["success_count"],
        "agent_runtime_results": runtime_report["results"],
    }


def run_agent_runtime_cases() -> dict[str, Any]:
    """Load the offline harness explicitly; no runtime mutation endpoint is exposed."""
    path = REPO_ROOT / "scripts" / "agent_runtime_benchmark.py"
    spec = importlib.util.spec_from_file_location("ctv_one_agent_runtime_benchmark", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Agent runtime benchmark harness could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return asyncio.run(module.run_runtime_benchmark())


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
        "model_selected": metrics.get("model_selected"),
        "model_role": metrics.get("model_role"),
        "model_routing_reason": metrics.get("model_routing_reason"),
        "model_routing_complexity": metrics.get("model_routing_complexity"),
        "model_fallback_used": metrics.get("model_fallback_used"),
        "model_fallback_reason": metrics.get("model_fallback_reason"),
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
        "cache_eligible": metrics.get("semantic_cache_eligible"),
        "cache_hit": metrics.get("semantic_cache_hit"),
        "cache_hit_type": metrics.get("semantic_cache_hit_type"),
        "cache_similarity_score": metrics.get("semantic_cache_similarity"),
        "cache_lookup_duration_ms": metrics.get("semantic_cache_lookup_duration_ms"),
        "cache_scope": metrics.get("semantic_cache_scope"),
        "ollama_skipped": metrics.get("ollama_skipped_due_to_cache"),
        "cache_write_duration_ms": metrics.get("semantic_cache_write_duration_ms"),
        "supervisor_mode": metrics.get("supervisor_mode"),
        "supervisor_planner_type": metrics.get("supervisor_planner_type"),
        "supervisor_task_count": metrics.get("supervisor_plan_task_count"),
        "supervisor_agents": metrics.get("supervisor_agents_selected", []),
        "supervisor_planning_duration_ms": metrics.get("supervisor_planning_duration_ms"),
        "supervisor_execution_duration_ms": metrics.get("supervisor_execution_duration_ms"),
        "supervisor_composition_duration_ms": metrics.get("supervisor_composition_duration_ms"),
        "supervisor_total_duration_ms": metrics.get("supervisor_total_duration_ms"),
        "supervisor_parallelism_peak": metrics.get("supervisor_parallelism_peak"),
        "supervisor_fallback_used": metrics.get("supervisor_fallback_used"),
        "supervisor_partial_result": metrics.get("supervisor_partial_result"),
        "inference_queue_wait_ms": metrics.get("inference_queue_wait_ms"),
        "agent_runtime_selected_agents": metrics.get(
            "agent_runtime_selected_agents", []
        ),
        "agent_runtime_agent_versions": metrics.get(
            "agent_runtime_agent_versions", {}
        ),
        "agent_runtime_capabilities": metrics.get(
            "agent_runtime_capabilities", []
        ),
        "agent_runtime_budget_status": metrics.get(
            "agent_runtime_budget_status"
        ),
        "agent_runtime_task_outcomes": metrics.get(
            "agent_runtime_task_outcomes", []
        ),
        "agent_runtime_queue_wait_ms": metrics.get(
            "agent_runtime_queue_wait_ms"
        ),
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
            "case_order",
            "cache_pass",
            "success",
            "status_code",
            "duration_seconds",
            "error",
            "error_category",
            "safe_detail",
            "backend_request_id",
            "result_type",
            "benchmark_failure_injection",
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
            "cache_eligible",
            "cache_hit",
            "cache_hit_type",
            "cache_similarity_score",
            "cache_lookup_duration_ms",
            "cache_scope",
            "ollama_skipped",
            "cache_write_duration_ms",
            "supervisor_mode",
            "supervisor_planner_type",
            "supervisor_task_count",
            "supervisor_agents",
            "supervisor_planning_duration_ms",
            "supervisor_execution_duration_ms",
            "supervisor_composition_duration_ms",
            "supervisor_total_duration_ms",
            "supervisor_parallelism_peak",
            "supervisor_fallback_used",
            "supervisor_partial_result",
            "inference_queue_wait_ms",
            "agent_runtime_selected_agents",
            "agent_runtime_agent_versions",
            "agent_runtime_capabilities",
            "agent_runtime_budget_status",
            "agent_runtime_task_outcomes",
            "agent_runtime_queue_wait_ms",
            "model_selected",
            "model_role",
            "model_routing_reason",
            "model_routing_complexity",
            "model_fallback_used",
            "model_fallback_reason",
            "previous_model",
            "same_model_as_previous_case",
            "model_switch_from_previous_case",
            "first_request_for_model_in_run",
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
        "| # | Pass | Case | Result | Cache | Hit type | Lookup ms | Ollama skipped | Context | Prompt chars | Tokens | Model | Previous | "
        "Same model | First for model | Role | Complexity | Fallback | Budget | "
        "Parallel | Retrieval ms | Ops source | Snapshot age | Freshness | "
        "Saved est. ms | Degraded | Success | Status | "
        "Seconds | Sources | Ops tasks | Error |",
        "| ---: | --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | --- | --- | --- | --- | "
        "--- | --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | "
        "--- | --- | "
        "---: | ---: | ---: | --- |",
    ]
    for result in results:
        lines.append(
            "| {case_order} | {cache_pass} | {case_label} | {result_type} | {cache_hit} | {hit_type} | {lookup_ms} | {ollama_skipped} | {context} | {prompt_chars} | "
            "{tokens} | {model} | {previous_model} | {same_model} | {first_model} | "
            "{role} | {complexity} | {fallback} | {budget} | {parallel} | "
            "{retrieval_ms} | {ops_source} | {snapshot_age} | {freshness} | "
            "{saved_ms} | {degraded} | {success} | {status_code} | "
            "{duration_seconds} | {source_count} | {operational_tasks_used} | "
            "{error} |".format(
                case_label=result.get("case_label"),
                case_order=result.get("case_order") or "",
                cache_pass=result.get("cache_pass") or "",
                cache_hit=result.get("cache_hit"),
                hit_type=result.get("cache_hit_type") or "",
                lookup_ms=result.get("cache_lookup_duration_ms") or "",
                ollama_skipped=result.get("ollama_skipped"),
                result_type=result.get("result_type") or "",
                context=",".join(result.get("selected_context_types") or []),
                prompt_chars=result.get("final_prompt_chars") or "",
                tokens=result.get("estimated_prompt_tokens") or "",
                model=result.get("model_selected") or "",
                previous_model=result.get("previous_model") or "",
                same_model=result.get("same_model_as_previous_case"),
                first_model=result.get("first_request_for_model_in_run"),
                role=result.get("model_role") or "",
                complexity=result.get("model_routing_complexity") or "",
                fallback=result.get("model_fallback_used") or False,
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
