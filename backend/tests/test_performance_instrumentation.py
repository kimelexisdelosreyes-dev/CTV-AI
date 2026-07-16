import pytest

from app.services.performance_instrumentation import (
    AskPerformanceInstrumentation,
    estimate_input_tokens,
    prompt_character_count,
)


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


def test_collection_search_metrics_are_safe_counts_and_timings() -> None:
    instrumentation = AskPerformanceInstrumentation()

    instrumentation.record_collection_search("technical-documentation", 0.01, 3)

    fields = instrumentation.to_log_fields("success")
    searches = fields["routed_collection_searches"]

    assert searches == [
        {
            "collection": "technical-documentation",
            "duration_ms": 10.0,
            "retrieved_chunk_count": 3,
        }
    ]
