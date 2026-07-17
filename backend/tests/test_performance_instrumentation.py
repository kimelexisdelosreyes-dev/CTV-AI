import pytest

from app.services.performance_instrumentation import (
    AskPerformanceInstrumentation,
    estimate_input_tokens,
    prompt_character_count,
)
from app.services.service_errors import CompanyBrainServiceError


def test_measure_records_duration_with_injected_clock() -> None:
    times = iter([10.0, 10.125])
    instrumentation = AskPerformanceInstrumentation(clock=lambda: next(times))

    with instrumentation.measure("phase_ms"):
        pass

    assert instrumentation.durations_ms["phase_ms"] == pytest.approx(125.0)


def test_measure_accumulates_repeated_duration() -> None:
    times = iter([1.0, 1.01, 2.0, 2.02])
    instrumentation = AskPerformanceInstrumentation(clock=lambda: next(times))

    with instrumentation.measure("embedding_ms"):
        pass
    with instrumentation.measure("embedding_ms"):
        pass

    assert instrumentation.durations_ms["embedding_ms"] == pytest.approx(30.0)


def test_stage_report_uses_p1_stage_names_and_request_id() -> None:
    times = iter([1.0, 1.125, 2.0, 2.5])
    instrumentation = AskPerformanceInstrumentation(clock=lambda: next(times))

    with instrumentation.measure("total_request"):
        pass
    with instrumentation.measure("ollama_total"):
        pass
    instrumentation.mark_success()

    report = instrumentation.to_report()

    assert report["event"] == "company_brain_performance"
    assert report["request_id"] == instrumentation.request_id
    assert report["success"] is True
    assert report["total_seconds"] == pytest.approx(0.125)
    assert report["stages"] == {
        "total_request": pytest.approx(0.125),
        "ollama_total": pytest.approx(0.5),
    }
    assert instrumentation.durations_ms["total_endpoint_ms"] == pytest.approx(125.0)
    assert instrumentation.durations_ms["ollama_request_ms"] == pytest.approx(500.0)


def test_prompt_character_count_uses_content_only() -> None:
    messages = [
        {"role": "system", "content": "abcd"},
        {"role": "user", "content": "efghijkl"},
    ]

    assert prompt_character_count(messages) == 12
    assert estimate_input_tokens(12) == 3


def test_estimated_input_tokens_rounds_up() -> None:
    assert estimate_input_tokens(0) == 0
    assert estimate_input_tokens(1) == 1
    assert estimate_input_tokens(5) == 2


def test_safe_log_fields_do_not_include_prompt_or_answer_text() -> None:
    instrumentation = AskPerformanceInstrumentation()
    instrumentation.record_route("general", 0.45, ["company-policies"])
    instrumentation.record_prompt(
        [
            {"role": "system", "content": "never log this prompt"},
            {"role": "user", "content": "never log this document content"},
        ]
    )
    instrumentation.answer_character_count = len("never log this answer")

    fields = instrumentation.to_log_fields("success")

    assert fields["routed_intent"] == "general"
    assert fields["collection_count"] == 1
    assert fields["prompt_character_count"] == 52
    assert fields["answer_character_count"] == 21
    assert "never log this" not in str(fields)


def test_prompt_component_metrics_are_counts_only() -> None:
    instrumentation = AskPerformanceInstrumentation()

    instrumentation.record_prompt(
        [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "question plus knowledge"},
        ],
        system_prompt="system prompt",
        employee_context="employee",
        knowledge_context="knowledge",
        operational_context="ops",
        user_question="question",
    )

    report = instrumentation.to_report("success")
    metrics = report["metrics"]

    assert metrics["system_prompt_chars"] == 13
    assert metrics["employee_context_chars"] == 8
    assert metrics["knowledge_context_chars"] == 9
    assert metrics["operational_context_chars"] == 3
    assert metrics["user_question_chars"] == 8
    assert metrics["final_prompt_chars"] == 36
    assert metrics["estimated_prompt_tokens"] == 9
    assert "system prompt" not in str(report)


def test_absent_ollama_metrics_are_ignored() -> None:
    instrumentation = AskPerformanceInstrumentation()

    instrumentation.record_ollama_metrics({})

    report = instrumentation.to_report("success")
    assert "prompt_eval_count" not in report["metrics"]
    assert instrumentation.tokens_per_second() is None


def test_ollama_token_rate_uses_payload_metrics_when_available() -> None:
    instrumentation = AskPerformanceInstrumentation()

    instrumentation.record_ollama_metrics(
        {
            "prompt_eval_count": 100,
            "eval_count": 20,
            "eval_duration": 2_000_000_000,
            "load_duration": 10,
            "total_duration": 30,
        }
    )

    report = instrumentation.to_report("success")
    assert report["metrics"]["prompt_eval_count"] == 100
    assert report["metrics"]["eval_count"] == 20
    assert report["metrics"]["calculated_tokens_per_second"] == 10.0
    assert instrumentation.tokens_per_second() == 10.0


def test_stream_first_token_latency_starts_at_inference_not_request() -> None:
    times = iter([12.25, 13.0])
    instrumentation = AskPerformanceInstrumentation(clock=lambda: next(times))
    instrumentation.inference_started_at = 10.0

    instrumentation.record_first_stream_token()
    instrumentation.record_stream_completion(
        token_chunk_count=1,
        answer="visible answer",
    )

    assert instrumentation.metrics["first_token_latency_ms"] == 2250.0
    assert instrumentation.metrics["token_chunk_count"] == 1
    assert instrumentation.metrics["streamed_answer_chars"] == 14


def test_collection_search_metrics_are_safe_counts_and_timings() -> None:
    instrumentation = AskPerformanceInstrumentation()

    instrumentation.record_collection_search("technical-documentation", 0.01, 3)

    fields = instrumentation.to_log_fields("success")
    searches = fields["routed_collection_searches"]

    assert searches == [
        {
            "collection": "technical-documentation",
            "resolved_collection": None,
            "duration_ms": 10.0,
            "retrieved_chunk_count": 3,
        }
    ]


def test_failure_diagnostics_are_sanitized() -> None:
    instrumentation = AskPerformanceInstrumentation()
    error = CompanyBrainServiceError(
        category="model_inference_truncated",
        diagnostics={
            "message_keys": ["content", "thinking"],
            "message_content_chars": 0,
            "raw_text": {"unsafe": "do not serialize"},
            "answer": "secret answer text",
        },
    )

    instrumentation.mark_failure(error)
    fields = instrumentation.to_log_fields("error")

    assert fields["error_category"] == "model_inference_truncated"
    assert fields["error_diagnostics"]["message_keys"] == ["content", "thinking"]
    assert fields["error_diagnostics"]["message_content_chars"] == 0
    assert "raw_text" not in fields["error_diagnostics"]
    assert "secret answer text" not in str(fields)
