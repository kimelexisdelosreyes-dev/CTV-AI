from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from company_brain_baseline import PROMPTS, benchmark_url


DEFAULT_LOG_PATH = Path("logs") / "performance.jsonl"


def prompt_by_label(label: str) -> str:
    prompts = dict(PROMPTS)
    if label not in prompts:
        valid = ", ".join(sorted(prompts))
        raise ValueError(f"Unknown case label. Valid labels: {valid}")
    return prompts[label]


def read_performance_event(request_id: str, log_path: Path) -> dict[str, Any] | None:
    if not request_id or not log_path.exists():
        return None

    for line in reversed(log_path.read_text(encoding="utf-8").splitlines()):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("request_id") == request_id:
            return event
    return None


def call_case(
    api_root: str,
    bearer_token: str,
    case_label: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "question": prompt_by_label(case_label),
            "top_k": 5,
            "assistant": "general",
            "use_employee_context": True,
        }
    ).encode("utf-8")
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

    started = perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response.read()
            headers = response.headers
            status_code = response.status
            error_detail = None
    except HTTPError as exc:
        headers = exc.headers
        status_code = exc.code
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            payload = {}
        error_detail = payload.get("detail")
    except (URLError, TimeoutError) as exc:
        headers = {}
        status_code = None
        error_detail = type(exc).__name__

    request_id = headers.get("X-Request-ID") if headers else None
    error_category = headers.get("X-Error-Category") if headers else None
    result_type = headers.get("X-Result-Type") if headers else None

    return {
        "case_label": case_label,
        "request_id": request_id,
        "http_status": status_code,
        "duration_seconds": round(perf_counter() - started, 3),
        "result_type": result_type,
        "error_category": error_category,
        "safe_detail": error_detail,
    }


def summarize_event(event: dict[str, Any] | None) -> dict[str, Any]:
    if not event:
        return {}

    metrics = event.get("metrics") or {}
    requirements = event.get("context_requirements") or {}
    stages = event.get("stages") or {}
    return {
        "route": {
            "intent": event.get("routed_intent"),
            "confidence": event.get("routing_confidence"),
        },
        "retrieval": {
            "required_contexts": metrics.get("required_context_components", []),
            "selected_contexts": requirements.get("selected_context_types", []),
            "parallel_used": metrics.get("retrieval_parallel_used"),
            "component_durations_ms": {
                "knowledge": metrics.get("knowledge_retrieval_duration_ms"),
                "operations": metrics.get("operations_retrieval_duration_ms"),
                "employee": metrics.get("employee_retrieval_duration_ms"),
                "history": metrics.get("history_retrieval_duration_ms"),
            },
            "retrieval_wall_time_ms": metrics.get("retrieval_total_duration_ms"),
            "sequential_estimated_duration_ms": metrics.get(
                "sequential_estimated_duration_ms"
            ),
            "parallel_time_saved_estimate_ms": metrics.get(
                "parallel_time_saved_estimate_ms"
            ),
            "degraded": metrics.get("context_degraded"),
            "unavailable_components": metrics.get(
                "unavailable_context_components",
                [],
            ),
            "failed_components": metrics.get("failed_context_components", []),
            "timed_out_components": metrics.get(
                "timed_out_context_components",
                [],
            ),
        },
        "prompt": {
            "selected_context_types": requirements.get(
                "selected_context_types",
                [],
            ),
            "final_prompt_chars": metrics.get("final_prompt_chars"),
            "estimated_prompt_tokens": metrics.get("estimated_prompt_tokens"),
            "user_question_chars": metrics.get("user_question_chars"),
            "knowledge_context_chars": metrics.get("knowledge_context_chars"),
            "knowledge_chunks_final": metrics.get("knowledge_chunks_final"),
            "operational_context_chars": metrics.get("operational_context_chars"),
            "operational_tasks_final": metrics.get("operational_tasks_final"),
            "operations_context_source": metrics.get("operations_context_source"),
            "operations_snapshot_id": metrics.get("operations_snapshot_id"),
            "operations_snapshot_age_seconds": metrics.get(
                "operations_snapshot_age_seconds"
            ),
            "operations_snapshot_freshness": metrics.get(
                "operations_snapshot_freshness"
            ),
            "employee_context_included": requirements.get("include_employee"),
            "prompt_budget_applied": metrics.get("prompt_budget_applied"),
            "prompt_components_omitted": metrics.get("prompt_components_omitted"),
            "prompt_components_truncated": metrics.get("prompt_components_truncated"),
        },
        "ollama": {
            "selected_model": metrics.get("model_selected"),
            "model_role": metrics.get("model_role"),
            "complexity": metrics.get("model_routing_complexity"),
            "routing_reason": metrics.get("model_routing_reason"),
            "fallback_used": metrics.get("model_fallback_used"),
            "fallback_reason": metrics.get("model_fallback_reason"),
            "prompt_eval_count": metrics.get("prompt_eval_count"),
            "eval_count": metrics.get("eval_count"),
            "load_duration": metrics.get("load_duration"),
            "prompt_eval_duration": metrics.get("prompt_eval_duration"),
            "eval_duration": metrics.get("eval_duration"),
            "total_duration": metrics.get("total_duration"),
            "tokens_per_second": metrics.get("tokens_per_second"),
            "first_token_seconds": metrics.get("first_token_seconds"),
        },
        "timing": {
            "prompt_assembly_duration_ms": seconds_to_ms(stages.get("prompt_builder")),
            "inference_duration_ms": seconds_to_ms(stages.get("ollama_total")),
            "total_duration_ms": seconds_to_ms(stages.get("total_request")),
        },
        "error_diagnostics": event.get("error_diagnostics") or {},
    }


def seconds_to_ms(value: Any) -> float | None:
    if isinstance(value, int | float):
        return round(float(value) * 1000, 3)
    return None


def main() -> int:
    api_root = (os.getenv("CTV_ONE_API_ROOT") or "").rstrip("/")
    token = os.getenv("CTV_ONE_BEARER_TOKEN") or ""
    case_label = os.getenv("CTV_ONE_BENCHMARK_CASE") or ""
    timeout_seconds = float(os.getenv("CTV_ONE_BENCHMARK_TIMEOUT_SECONDS", "420"))
    log_path = Path(os.getenv("CTV_ONE_PERFORMANCE_LOG_PATH", str(DEFAULT_LOG_PATH)))

    if not api_root or not token or not case_label:
        print(
            "Set CTV_ONE_API_ROOT, CTV_ONE_BEARER_TOKEN, and CTV_ONE_BENCHMARK_CASE.",
            file=sys.stderr,
        )
        return 2

    result = call_case(api_root, token, case_label, timeout_seconds)
    event = read_performance_event(str(result.get("request_id") or ""), log_path)
    print(json.dumps({**result, **summarize_event(event)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
