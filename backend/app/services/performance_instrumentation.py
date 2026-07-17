import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from app.core.config import settings
from app.core.context_requirements import ContextRequirements

if TYPE_CHECKING:
    from app.services.model_router import ModelRoutingDecision


REQUEST_STAGES = (
    "authentication",
    "intelligence_router",
    "context_retrieval",
    "employee_context",
    "knowledge_retrieval",
    "operational_context",
    "history_loading",
    "prompt_builder",
    "ollama_total",
    "response_formatting",
    "total_request",
)

LEGACY_STAGE_ALIASES = {
    "total_endpoint_ms": "total_request",
    "intelligence_router_ms": "intelligence_router",
    "employee_context_ms": "employee_context",
    "monday_operational_context_ms": "operational_context",
    "history_loading_ms": "history_loading",
    "prompt_assembly_ms": "prompt_builder",
    "ollama_request_ms": "ollama_total",
}

STAGE_LEGACY_FIELDS = {
    "total_request": "total_endpoint_ms",
    "intelligence_router": "intelligence_router_ms",
    "employee_context": "employee_context_ms",
    "operational_context": "monday_operational_context_ms",
    "history_loading": "history_loading_ms",
    "prompt_builder": "prompt_assembly_ms",
    "ollama_total": "ollama_request_ms",
}

OLLAMA_METRIC_FIELDS = (
    "prompt_eval_count",
    "eval_count",
    "prompt_eval_duration",
    "eval_duration",
    "load_duration",
    "total_duration",
)

SAFE_DIAGNOSTIC_FIELDS = {
    "http_status",
    "content_type",
    "json_ok",
    "raw_response_chars",
    "top_level_keys",
    "message_present",
    "message_type",
    "message_keys",
    "message_content_present",
    "message_content_type",
    "message_content_chars",
    "message_thinking_present",
    "message_thinking_type",
    "message_thinking_chars",
    "response_field_present",
    "response_field_type",
    "response_field_chars",
    "done",
    "done_reason",
    "model",
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
    "has_error",
}


@dataclass(frozen=True)
class CollectionSearchMetric:
    collection: str | None
    duration_ms: float
    retrieved_chunk_count: int
    resolved_collection: str | None = None


@dataclass
class AskPerformanceInstrumentation:
    enabled: bool = True
    clock: Callable[[], float] = perf_counter
    request_id: str = field(default_factory=lambda: str(uuid4()))
    durations_ms: dict[str, float] = field(default_factory=dict)
    stage_durations: dict[str, float] = field(default_factory=dict)
    metrics: dict[str, object] = field(default_factory=dict)
    collection_searches: list[CollectionSearchMetric] = field(default_factory=list)
    success: bool | None = None
    error_type: str | None = None
    error_category: str | None = None
    error_diagnostics: dict[str, object] = field(default_factory=dict)
    routed_intent: str | None = None
    routing_confidence: float | None = None
    collection_count: int = 0
    retrieved_chunk_count: int = 0
    operational_task_count: int = 0
    prompt_character_count: int = 0
    estimated_input_token_count: int = 0
    estimated_output_token_count: int = 0
    answer_character_count: int = 0
    model_name: str | None = None
    context_requirements: dict[str, object] = field(default_factory=dict)
    prompt_components_omitted: list[str] = field(default_factory=list)
    prompt_components_truncated: list[str] = field(default_factory=list)
    request_started_at: float = field(default_factory=perf_counter)
    inference_started_at: float | None = None

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        if not self.enabled:
            yield
            return

        started_at = self.clock()
        try:
            yield
        finally:
            self.add_duration(name, self.clock() - started_at)

    def add_duration(self, name: str, elapsed_seconds: float) -> None:
        if not self.enabled:
            return
        elapsed_seconds = max(elapsed_seconds, 0.0)
        elapsed_ms = max(elapsed_seconds * 1000, 0.0)
        self.durations_ms[name] = self.durations_ms.get(name, 0.0) + elapsed_ms
        stage_name = canonical_stage_name(name)
        if stage_name:
            self.stage_durations[stage_name] = (
                self.stage_durations.get(stage_name, 0.0) + elapsed_seconds
            )
            legacy_name = STAGE_LEGACY_FIELDS.get(stage_name)
            if legacy_name and legacy_name != name:
                self.durations_ms[legacy_name] = (
                    self.durations_ms.get(legacy_name, 0.0) + elapsed_ms
                )

    def record_route(
        self,
        intent: str,
        confidence: float,
        collections: list[str],
    ) -> None:
        if not self.enabled:
            return
        self.routed_intent = intent
        self.routing_confidence = confidence
        self.collection_count = len(collections)

    def record_collection_search(
        self,
        collection: str | None,
        elapsed_seconds: float,
        retrieved_chunk_count: int,
        resolved_collection: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        self.collection_searches.append(
            CollectionSearchMetric(
                collection=collection,
                duration_ms=max(elapsed_seconds * 1000, 0.0),
                retrieved_chunk_count=retrieved_chunk_count,
                resolved_collection=resolved_collection,
            )
        )

    def record_metric(self, name: str, value: object | None) -> None:
        if not self.enabled or value is None:
            return
        if not is_safe_metric_value(value):
            return
        self.metrics[name] = value

    def record_context_requirements(
        self,
        requirements: ContextRequirements,
    ) -> None:
        if not self.enabled:
            return
        self.context_requirements = requirements.to_safe_dict()
        for key, value in self.context_requirements.items():
            self.record_metric(f"context_{key}", value)

    def record_prompt_budget(
        self,
        *,
        applied: bool,
        omitted: list[str],
        truncated: list[str],
    ) -> None:
        if not self.enabled:
            return
        self.prompt_components_omitted = list(omitted)
        self.prompt_components_truncated = list(truncated)
        self.metrics["prompt_budget_applied"] = int(applied)
        self.metrics["prompt_components_omitted"] = list(omitted)
        self.metrics["prompt_components_truncated"] = list(truncated)

    def record_context_retrieval(
        self,
        *,
        parallel_execution_used: bool,
        component_durations_ms: dict[str, float],
        total_retrieval_duration_ms: float,
        required_components: list[str],
        successful_components: list[str],
        failed_components: list[str],
        timed_out_components: list[str],
        context_degraded: bool,
        unavailable_components: list[str],
        required_context_failure: str | None,
    ) -> None:
        if not self.enabled:
            return

        sequential_estimate = sum(
            duration
            for component, duration in component_durations_ms.items()
            if component in successful_components
        )
        time_saved = max(sequential_estimate - total_retrieval_duration_ms, 0.0)

        self.record_metric("retrieval_parallel_used", parallel_execution_used)
        self.record_metric("retrieval_total_duration_ms", total_retrieval_duration_ms)
        self.record_metric("required_context_components", list(required_components))
        self.record_metric("successful_context_components", list(successful_components))
        self.record_metric("failed_context_components", list(failed_components))
        self.record_metric("timed_out_context_components", list(timed_out_components))
        self.record_metric("context_degraded", context_degraded)
        self.record_metric(
            "unavailable_context_components",
            list(unavailable_components),
        )
        self.record_metric("required_context_failure", required_context_failure)
        self.record_metric("sequential_estimated_duration_ms", sequential_estimate)
        self.record_metric("parallel_time_saved_estimate_ms", time_saved)

        for component, duration_ms in component_durations_ms.items():
            self.record_metric(f"{component}_retrieval_duration_ms", duration_ms)

    def record_inference_start(self) -> None:
        if not self.enabled:
            return
        self.inference_started_at = self.clock()
        self.record_metric(
            "inference_start_offset_ms",
            max((self.inference_started_at - self.request_started_at) * 1000, 0.0),
        )

    def record_model_routing(self, decision: "ModelRoutingDecision") -> None:
        if not self.enabled:
            return
        self.model_name = decision.selected_model
        self.record_metric("model_router_enabled", settings.ctv_one_model_router_enabled)
        self.record_metric("model_selected", decision.selected_model)
        self.record_metric("model_role", decision.model_role)
        self.record_metric("model_routing_reason", decision.routing_reason)
        self.record_metric("model_routing_confidence", decision.confidence)
        self.record_metric("model_routing_complexity", decision.complexity)
        self.record_metric("model_fallback_used", decision.fallback_used)
        self.record_metric("model_fallback_reason", decision.fallback_reason)
        self.record_metric(
            "model_availability_checked",
            decision.availability_checked,
        )
        self.record_metric(
            "model_routing_duration_ms",
            decision.routing_duration_ms,
        )

    def record_stream_started(self) -> None:
        if not self.enabled:
            return
        self.record_metric("response_mode", "streaming")
        self.record_metric("stream_started_at", datetime.now(timezone.utc).isoformat())

    def record_context_ready(self) -> None:
        if not self.enabled:
            return
        self.record_metric(
            "context_ready_offset_ms",
            max((self.clock() - self.request_started_at) * 1000, 0.0),
        )

    def record_first_stream_token(self) -> None:
        if not self.enabled or "first_token_latency_ms" in self.metrics:
            return
        if self.inference_started_at is None:
            return
        self.record_metric(
            "first_token_latency_ms",
            max((self.clock() - self.inference_started_at) * 1000, 0.0),
        )

    def record_stream_completion(
        self,
        *,
        token_chunk_count: int,
        answer: str,
        cancelled: bool = False,
        error_category: str | None = None,
        assistant_persisted: bool = False,
    ) -> None:
        if not self.enabled:
            return
        self.record_metric("token_chunk_count", token_chunk_count)
        self.record_metric("streamed_answer_chars", len(answer))
        self.record_metric("stream_completed", not cancelled and error_category is None)
        self.record_metric("stream_cancelled", cancelled)
        self.record_metric("stream_error_category", error_category)
        self.record_metric("assistant_persisted", assistant_persisted)
        self.record_metric("partial_assistant_saved", False)
        self.record_metric(
            "streaming_duration_ms",
            max((self.clock() - self.request_started_at) * 1000, 0.0),
        )

    def record_prompt(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        employee_context: str | None = None,
        knowledge_context: str | None = None,
        operational_context: str | None = None,
        history_context: str | None = None,
        user_question: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        character_count = prompt_character_count(messages)
        self.prompt_character_count = character_count
        self.estimated_input_token_count = estimate_input_tokens(character_count)
        self.metrics["final_prompt_chars"] = character_count
        self.metrics["estimated_prompt_tokens"] = self.estimated_input_token_count

        prompt_components = {
            "system_prompt_chars": system_prompt,
            "employee_context_chars": employee_context,
            "knowledge_context_chars": knowledge_context,
            "operational_context_chars": operational_context,
            "history_context_chars": history_context,
            "user_question_chars": user_question,
        }
        for metric_name, text_value in prompt_components.items():
            if text_value is not None:
                self.metrics[metric_name] = len(text_value)
            else:
                self.metrics.setdefault(metric_name, 0)

    def record_answer(self, answer: str) -> None:
        if not self.enabled:
            return
        self.answer_character_count = len(answer)
        self.estimated_output_token_count = estimate_input_tokens(
            self.answer_character_count
        )

    def record_ollama_metrics(self, payload: dict[str, object] | None) -> None:
        if not self.enabled or not isinstance(payload, dict):
            return

        for field_name in OLLAMA_METRIC_FIELDS:
            value = payload.get(field_name)
            if isinstance(value, int | float):
                self.metrics[field_name] = value

        eval_count = self.metrics.get("eval_count")
        eval_duration = self.metrics.get("eval_duration")
        if (
            isinstance(eval_count, int | float)
            and isinstance(eval_duration, int | float)
            and eval_count > 0
            and eval_duration > 0
        ):
            calculated = round(eval_count / (eval_duration / 1_000_000_000), 3)
            self.metrics["calculated_tokens_per_second"] = calculated
            self.metrics["tokens_per_second"] = calculated

    def mark_success(self) -> None:
        if not self.enabled:
            return
        self.success = True
        self.error_type = None
        self.error_category = None
        self.error_diagnostics = {}

    def mark_failure(self, error: BaseException) -> None:
        if not self.enabled:
            return
        self.success = False
        self.error_type = type(error).__name__
        self.error_category = getattr(error, "category", self.error_type)
        self.error_diagnostics = safe_diagnostics(
            getattr(error, "diagnostics", {})
        )

    def tokens_per_second(self) -> float | None:
        actual = self.metrics.get("calculated_tokens_per_second")
        if isinstance(actual, int | float):
            return rounded_ms(float(actual))

        ollama_ms = self.durations_ms.get("ollama_request_ms", 0.0)
        if ollama_ms <= 0 or self.estimated_output_token_count <= 0:
            return None
        return rounded_ms(self.estimated_output_token_count / (ollama_ms / 1000))

    def to_report(self, outcome: str | None = None) -> dict[str, object]:
        success = self.success
        if success is None and outcome is not None:
            success = outcome == "success"

        metrics = dict(self.metrics)
        metrics.setdefault("final_prompt_chars", self.prompt_character_count)
        metrics.setdefault("estimated_prompt_tokens", self.estimated_input_token_count)
        metrics.setdefault("estimated_output_tokens", self.estimated_output_token_count)
        token_rate = self.tokens_per_second()
        if token_rate is not None:
            metrics.setdefault("tokens_per_second", token_rate)

        total_seconds = self.stage_durations.get("total_request", 0.0)

        return {
            "event": "company_brain_performance",
            "request_id": self.request_id,
            "success": success,
            "error_type": self.error_type,
            "error_category": self.error_category,
            "error_diagnostics": self.error_diagnostics,
            "context_requirements": self.context_requirements,
            "prompt_components_omitted": self.prompt_components_omitted,
            "prompt_components_truncated": self.prompt_components_truncated,
            "total_seconds": rounded_seconds(total_seconds),
            "stages": {
                stage: rounded_seconds(duration)
                for stage, duration in self.stage_durations.items()
                if stage in REQUEST_STAGES
            },
            "metrics": metrics,
        }

    def to_log_fields(self, outcome: str) -> dict[str, object]:
        report = self.to_report(outcome)
        fields: dict[str, object] = {
            **report,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome,
            "total_endpoint_ms": rounded_ms(
                self.durations_ms.get("total_endpoint_ms", 0.0)
            ),
            "intelligence_router_ms": rounded_ms(
                self.durations_ms.get("intelligence_router_ms", 0.0)
            ),
            "employee_context_ms": rounded_ms(
                self.durations_ms.get("employee_context_ms", 0.0)
            ),
            "monday_operational_context_ms": rounded_ms(
                self.durations_ms.get("monday_operational_context_ms", 0.0)
            ),
            "embedding_ms": rounded_ms(self.durations_ms.get("embedding_ms", 0.0)),
            "qdrant_vector_search_ms": rounded_ms(
                self.durations_ms.get("qdrant_vector_search_ms", 0.0)
            ),
            "history_loading_ms": rounded_ms(
                self.durations_ms.get("history_loading_ms", 0.0)
            ),
            "prompt_assembly_ms": rounded_ms(
                self.durations_ms.get("prompt_assembly_ms", 0.0)
            ),
            "ollama_request_ms": rounded_ms(
                self.durations_ms.get("ollama_request_ms", 0.0)
            ),
            "routed_intent": self.routed_intent,
            "routing_confidence": self.routing_confidence,
            "collection_count": self.collection_count,
            "retrieved_chunk_count": self.retrieved_chunk_count,
            "operational_task_count": self.operational_task_count,
            "model_name": self.model_name,
            "prompt_size": self.prompt_character_count,
            "prompt_character_count": self.prompt_character_count,
            "estimated_input_token_count": self.estimated_input_token_count,
            "estimated_output_token_count": self.estimated_output_token_count,
            "tokens_per_second": self.tokens_per_second(),
            "answer_character_count": self.answer_character_count,
            "gpu_utilization": None,
            "cpu_utilization": None,
            "routed_collection_searches": [
                {
                    "collection": item.collection,
                    "resolved_collection": item.resolved_collection,
                    "duration_ms": rounded_ms(item.duration_ms),
                    "retrieved_chunk_count": item.retrieved_chunk_count,
                }
                for item in self.collection_searches
            ],
        }
        return fields


def canonical_stage_name(name: str) -> str | None:
    if name in REQUEST_STAGES:
        return name
    return LEGACY_STAGE_ALIASES.get(name)


def prompt_character_count(messages: list[dict[str, str]]) -> int:
    return sum(len(message.get("content", "")) for message in messages)


def estimate_input_tokens(character_count: int) -> int:
    if character_count <= 0:
        return 0
    return math.ceil(character_count / 4)


def rounded_ms(value: float) -> float:
    return round(value, 3)


def rounded_seconds(value: float) -> float:
    return round(value, 6)


def is_safe_metric_value(value: object) -> bool:
    if isinstance(value, str | int | float | bool) or value is None:
        return True
    if isinstance(value, list):
        return all(isinstance(item, str | int | float | bool) or item is None for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and (isinstance(item, str | int | float | bool) or item is None)
            for key, item in value.items()
        )
    return False


def safe_diagnostics(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}

    safe: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or key not in SAFE_DIAGNOSTIC_FIELDS:
            continue
        if isinstance(item, str | int | float | bool) or item is None:
            safe[key] = item
        elif isinstance(item, list) and all(
            isinstance(part, str | int | float | bool) or part is None
            for part in item
        ):
            safe[key] = item
    return safe
