import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter


@dataclass(frozen=True)
class CollectionSearchMetric:
    collection: str | None
    duration_ms: float
    retrieved_chunk_count: int


@dataclass
class AskPerformanceInstrumentation:
    enabled: bool = True
    clock: Callable[[], float] = perf_counter
    durations_ms: dict[str, float] = field(default_factory=dict)
    collection_searches: list[CollectionSearchMetric] = field(default_factory=list)
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
        elapsed_ms = max(elapsed_seconds * 1000, 0.0)
        self.durations_ms[name] = self.durations_ms.get(name, 0.0) + elapsed_ms

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
    ) -> None:
        if not self.enabled:
            return
        self.collection_searches.append(
            CollectionSearchMetric(
                collection=collection,
                duration_ms=max(elapsed_seconds * 1000, 0.0),
                retrieved_chunk_count=retrieved_chunk_count,
            )
        )

    def record_prompt(self, messages: list[dict[str, str]]) -> None:
        if not self.enabled:
            return
        character_count = prompt_character_count(messages)
        self.prompt_character_count = character_count
        self.estimated_input_token_count = estimate_input_tokens(character_count)

    def record_answer(self, answer: str) -> None:
        if not self.enabled:
            return
        self.answer_character_count = len(answer)
        self.estimated_output_token_count = estimate_input_tokens(
            self.answer_character_count
        )

    def tokens_per_second(self) -> float | None:
        ollama_ms = self.durations_ms.get("ollama_request_ms", 0.0)
        if ollama_ms <= 0 or self.estimated_output_token_count <= 0:
            return None
        return rounded_ms(self.estimated_output_token_count / (ollama_ms / 1000))

    def to_log_fields(self, outcome: str) -> dict[str, object]:
        fields: dict[str, object] = {
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
                    "duration_ms": rounded_ms(item.duration_ms),
                    "retrieved_chunk_count": item.retrieved_chunk_count,
                }
                for item in self.collection_searches
            ],
        }
        return fields


def prompt_character_count(messages: list[dict[str, str]]) -> int:
    return sum(len(message.get("content", "")) for message in messages)


def estimate_input_tokens(character_count: int) -> int:
    if character_count <= 0:
        return 0
    return math.ceil(character_count / 4)


def rounded_ms(value: float) -> float:
    return round(value, 3)
