from __future__ import annotations

from collections import Counter, deque
from statistics import median
from threading import RLock
from typing import Any

from app.services.performance_instrumentation import (
    SAFE_DIAGNOSTIC_FIELDS,
    is_safe_metric_value,
)


MAX_PERFORMANCE_EVENTS = 50

SAFE_EVENT_FIELDS = {
    "event",
    "request_id",
    "success",
    "error_type",
    "error_category",
    "error_diagnostics",
    "context_requirements",
    "prompt_components_omitted",
    "prompt_components_truncated",
    "total_seconds",
    "stages",
    "metrics",
    "timestamp",
    "outcome",
    "routed_intent",
    "routing_confidence",
    "total_endpoint_ms",
    "intelligence_router_ms",
    "employee_context_ms",
    "monday_operational_context_ms",
    "embedding_ms",
    "qdrant_vector_search_ms",
    "history_loading_ms",
    "prompt_assembly_ms",
    "ollama_request_ms",
    "prompt_character_count",
    "prompt_size",
    "estimated_input_token_count",
    "estimated_output_token_count",
    "tokens_per_second",
    "answer_character_count",
    "collection_count",
    "retrieved_chunk_count",
    "operational_task_count",
    "routed_collection_searches",
    "model_name",
    "gpu_utilization",
    "cpu_utilization",
}

STAGE_FIELDS = {
    "intelligence_router_ms": "intelligence_router",
    "employee_context_ms": "employee_context",
    "monday_operational_context_ms": "monday_operational_context",
    "embedding_ms": "embedding",
    "qdrant_vector_search_ms": "qdrant_vector_search",
    "history_loading_ms": "history_loading",
    "prompt_assembly_ms": "prompt_assembly",
    "ollama_request_ms": "ollama_request",
}


class PerformanceEventStore:
    def __init__(self, max_events: int = MAX_PERFORMANCE_EVENTS) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._enabled = False
        self._lock = RLock()

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_enabled(self, enabled: bool) -> bool:
        with self._lock:
            self._enabled = enabled
            return self._enabled

    def record(self, event: dict[str, Any]) -> None:
        with self._lock:
            if not self._enabled:
                return
            self._events.append(sanitize_event(event))

    def recent(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._events))

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def summary(self) -> dict[str, Any]:
        with self._lock:
            events = list(self._events)
        return summarize_events(events)


def sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    clean = {key: event.get(key) for key in SAFE_EVENT_FIELDS}
    clean["stages"] = {
        key: value
        for key, value in (event.get("stages") or {}).items()
        if isinstance(key, str) and isinstance(value, int | float)
    }
    clean["metrics"] = {
        key: value
        for key, value in (event.get("metrics") or {}).items()
        if isinstance(key, str) and is_safe_metric_value(value)
    }
    clean["context_requirements"] = {
        key: value
        for key, value in (event.get("context_requirements") or {}).items()
        if isinstance(key, str) and is_safe_metric_value(value)
    }
    clean["prompt_components_omitted"] = [
        item
        for item in event.get("prompt_components_omitted", [])
        if isinstance(item, str)
    ]
    clean["prompt_components_truncated"] = [
        item
        for item in event.get("prompt_components_truncated", [])
        if isinstance(item, str)
    ]
    clean["error_diagnostics"] = {
        key: value
        for key, value in (event.get("error_diagnostics") or {}).items()
        if isinstance(key, str)
        and key in SAFE_DIAGNOSTIC_FIELDS
        and (
            isinstance(value, str | int | float | bool)
            or value is None
            or (
                isinstance(value, list)
                and all(
                    isinstance(item, str | int | float | bool) or item is None
                    for item in value
                )
            )
        )
    }
    clean["routed_collection_searches"] = [
        {
            "collection": item.get("collection"),
            "resolved_collection": item.get("resolved_collection"),
            "duration_ms": item.get("duration_ms"),
            "retrieved_chunk_count": item.get("retrieved_chunk_count"),
        }
        for item in event.get("routed_collection_searches", [])
        if isinstance(item, dict)
    ]
    return clean


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * percentile_value) - 1))
    return round(ordered[index], 3)


def numeric_values(events: list[dict[str, Any]], field: str) -> list[float]:
    return [
        float(event[field])
        for event in events
        if isinstance(event.get(field), int | float)
    ]


def slowest_stage(events: list[dict[str, Any]]) -> str | None:
    totals = {
        label: sum(numeric_values(events, field))
        for field, label in STAGE_FIELDS.items()
    }
    if not totals or max(totals.values(), default=0.0) <= 0:
        return None
    return max(totals.items(), key=lambda item: item[1])[0]


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    total_durations = numeric_values(events, "total_endpoint_ms")
    outcomes = Counter(str(event.get("outcome") or "") for event in events)
    intents = Counter(str(event.get("routed_intent") or "unknown") for event in events)
    token_counts = numeric_values(events, "estimated_input_token_count")
    token_rates = numeric_values(events, "tokens_per_second")

    return {
        "request_count": len(events),
        "success_count": outcomes.get("success", 0),
        "failure_count": outcomes.get("error", 0),
        "average_total_duration_ms": average(total_durations),
        "median_total_duration_ms": round(median(total_durations), 3)
        if total_durations
        else 0.0,
        "p95_total_duration_ms": percentile(total_durations, 0.95),
        "average_ollama_duration_ms": average(
            numeric_values(events, "ollama_request_ms")
        ),
        "average_monday_duration_ms": average(
            numeric_values(events, "monday_operational_context_ms")
        ),
        "average_employee_context_duration_ms": average(
            numeric_values(events, "employee_context_ms")
        ),
        "average_embedding_duration_ms": average(numeric_values(events, "embedding_ms")),
        "average_qdrant_duration_ms": average(
            numeric_values(events, "qdrant_vector_search_ms")
        ),
        "average_estimated_input_tokens": average(token_counts),
        "average_tokens_per_second": average(token_rates),
        "slowest_stage": slowest_stage(events),
        "counts_by_routed_intent": dict(sorted(intents.items())),
    }


performance_event_store = PerformanceEventStore()
