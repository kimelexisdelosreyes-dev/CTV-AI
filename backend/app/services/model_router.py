import asyncio
import re
from dataclasses import dataclass
from time import monotonic, perf_counter
from typing import Literal

from app.core.config import settings
from app.services.ollama_service import OllamaServiceError, ollama_service


ModelComplexity = Literal["simple", "moderate", "complex"]


@dataclass(frozen=True)
class ModelRoutingInput:
    question: str
    intent: str
    include_knowledge: bool
    include_operations: bool
    include_employee: bool
    source_count: int
    operations_task_count: int
    final_prompt_chars: int
    estimated_prompt_tokens: int
    streaming: bool
    explicit_model: str | None = None


@dataclass(frozen=True)
class ModelRoutingDecision:
    selected_model: str
    model_role: str
    routing_reason: str
    confidence: Literal["high", "medium", "low"]
    complexity: ModelComplexity
    fallback_used: bool
    fallback_reason: str | None
    availability_checked: bool
    routing_duration_ms: float


COMPLEX_TERMS = {
    "analyze",
    "analysis",
    "recommend",
    "recommendation",
    "strategy",
    "strategic",
    "forecast",
    "risk",
    "risks",
    "tradeoff",
    "tradeoffs",
    "why",
    "executive summary",
    "scenario",
}
MODERATE_TERMS = {
    "compare",
    "comparison",
    "prioritize",
    "priorities",
    "plan",
    "multiple",
    "across",
}


def _contains_term(question: str, terms: set[str]) -> bool:
    normalized = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
    padded = f" {normalized} "
    return any(f" {term} " in padded for term in terms)


class ModelRouter:
    def __init__(self) -> None:
        self._availability_lock = asyncio.Lock()
        self._available_models: set[str] | None = None
        self._availability_expires_at = 0.0

    def clear_availability_cache(self) -> None:
        self._available_models = None
        self._availability_expires_at = 0.0

    def classify_complexity(self, routing_input: ModelRoutingInput) -> ModelComplexity:
        if (
            _contains_term(routing_input.question, COMPLEX_TERMS)
            or routing_input.final_prompt_chars >= 4_000
            or routing_input.estimated_prompt_tokens >= 1_000
            or routing_input.source_count >= 6
        ):
            return "complex"
        if (
            _contains_term(routing_input.question, MODERATE_TERMS)
            or routing_input.final_prompt_chars >= 1_600
            or routing_input.estimated_prompt_tokens >= 400
            or routing_input.source_count >= 3
            or (
                routing_input.include_knowledge
                and routing_input.include_operations
            )
        ):
            return "moderate"
        return "simple"

    def _configured_default(self) -> str:
        return settings.ctv_one_model_default or settings.ollama_model

    def _configured_model(self, role: str) -> str | None:
        return {
            "fast": settings.ctv_one_model_fast,
            "balanced": settings.ctv_one_model_balanced,
            "reasoning": settings.ctv_one_model_reasoning,
            "operations": settings.ctv_one_model_operations,
            "knowledge": settings.ctv_one_model_knowledge,
            "fallback": self._configured_default(),
        }.get(role)

    def _role(
        self,
        routing_input: ModelRoutingInput,
        complexity: ModelComplexity,
    ) -> tuple[str, str]:
        explicit_complex = _contains_term(routing_input.question, COMPLEX_TERMS)
        mixed_context = (
            routing_input.include_knowledge and routing_input.include_operations
        )
        if complexity == "complex" and (explicit_complex or not mixed_context):
            return "reasoning", "complex_request"
        if mixed_context:
            return "balanced", "mixed_operations_and_knowledge"
        if routing_input.include_operations:
            return "operations", "operations_context"
        if routing_input.include_knowledge:
            return "knowledge", "knowledge_context"
        if routing_input.include_employee:
            return "fast", "employee_context"
        if routing_input.intent == "general":
            return "fallback", "unsupported_route"
        return "fast", "simple_request"

    async def _models(self) -> tuple[set[str] | None, bool]:
        now = monotonic()
        if self._available_models is not None and now < self._availability_expires_at:
            return self._available_models, False
        async with self._availability_lock:
            now = monotonic()
            if self._available_models is not None and now < self._availability_expires_at:
                return self._available_models, False
            try:
                available = await ollama_service.list_models()
            except OllamaServiceError:
                return None, True
            self._available_models = available
            self._availability_expires_at = now + max(
                settings.ctv_one_model_availability_ttl_seconds,
                1.0,
            )
            return available, True

    async def route(self, routing_input: ModelRoutingInput) -> ModelRoutingDecision:
        started = perf_counter()
        complexity = self.classify_complexity(routing_input)

        if routing_input.explicit_model:
            return self._decision(
                selected_model=routing_input.explicit_model,
                model_role="explicit",
                routing_reason="explicit_model_override",
                confidence="high",
                complexity=complexity,
                fallback_used=False,
                fallback_reason=None,
                availability_checked=False,
                started=started,
            )

        if not settings.ctv_one_model_router_enabled:
            return self._decision(
                selected_model=settings.ollama_model,
                model_role="fallback",
                routing_reason="router_disabled",
                confidence="high",
                complexity=complexity,
                fallback_used=True,
                fallback_reason="router_disabled",
                availability_checked=False,
                started=started,
            )

        role, reason = self._role(routing_input, complexity)
        selected = self._configured_model(role)
        fallback_used = role == "fallback"
        fallback_reason = "unsupported_route" if role == "fallback" else None
        if not selected:
            selected = self._configured_default()
            fallback_used = True
            fallback_reason = "model_not_configured"

        available: set[str] | None = None
        checked_now = False
        if fallback_reason != "model_not_configured":
            available, checked_now = await self._models()
        if available is not None and selected not in available:
            default_model = self._configured_default()
            fallback_used = True
            fallback_reason = "model_unavailable"
            selected = default_model
            if default_model not in available and settings.ollama_model in available:
                selected = settings.ollama_model

        confidence: Literal["high", "medium", "low"] = (
            "high" if complexity in {"simple", "complex"} else "medium"
        )
        return self._decision(
            selected_model=selected,
            model_role=role if not fallback_used else "fallback",
            routing_reason=reason,
            confidence=confidence,
            complexity=complexity,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            availability_checked=checked_now,
            started=started,
        )

    @staticmethod
    def _decision(
        *,
        selected_model: str,
        model_role: str,
        routing_reason: str,
        confidence: Literal["high", "medium", "low"],
        complexity: ModelComplexity,
        fallback_used: bool,
        fallback_reason: str | None,
        availability_checked: bool,
        started: float,
    ) -> ModelRoutingDecision:
        return ModelRoutingDecision(
            selected_model=selected_model,
            model_role=model_role,
            routing_reason=routing_reason,
            confidence=confidence,
            complexity=complexity,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            availability_checked=availability_checked,
            routing_duration_ms=round((perf_counter() - started) * 1000, 3),
        )


model_router = ModelRouter()
