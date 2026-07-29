import asyncio
import logging
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

from app.ai_runtime import ExecutionPlan, RuntimeMessage, RuntimeRequest, RuntimeStatus
from app.ai_runtime.composition import build_local_ollama_runtime
from app.core.config import settings
from app.prompt_engine import PromptCompositionRequest, PromptMessage, default_prompt_composer
from app.atlas.bootstrap import atlas_shadow_mode_service
from app.schemas.chat import AssistantName
from app.services.ollama_service import (
    OllamaEmptyResponseError, OllamaInferenceTimeoutError, OllamaMalformedResponseError,
    OllamaServiceError, OllamaTruncatedResponseError, OllamaUpstreamError, ollama_service,
)
from app.shadow_mode import production_prompt_from_messages, shadow_request_id

logger = logging.getLogger(__name__)

MODEL_TO_ASSISTANT: dict[str, str] = {
    "ctv-ai-general": "general", "ctv-ai-production": "production", "ctv-ai-graphics": "graphics",
    "ctv-ai-drone": "drone", "ctv-ai-it": "it", "ctv-ai-comedy": "comedy",
}


@dataclass(frozen=True)
class RuntimeExecutionTrace:
    execution_id: str; plan_id: str; selected_model_id: str; adapter_id: str | None
    provider_type: str; location: str; duration_ms: int; final_status: str; finish_reason: str
    input_tokens: int | None; output_tokens: int | None; retry_count: int; fallback_count: int
    diagnostic_codes: tuple[str, ...]


class AIRouter:
    def __init__(self, *, ollama=None, runtime=None, runtime_enabled: bool | None = None, shadow_service=None, prompt_composer=None) -> None:
        self._ollama = ollama or ollama_service
        self._runtime = runtime
        self._runtime_enabled = settings.ctv_one_ai_runtime_enabled if runtime_enabled is None else runtime_enabled
        self._shadow_service = shadow_service or atlas_shadow_mode_service
        self._prompt_composer = prompt_composer or default_prompt_composer()

    @staticmethod
    def supported_models() -> list[str]: return ["ctv-ai-auto", *MODEL_TO_ASSISTANT]
    @staticmethod
    def assistant_for_model(model: str) -> str: return MODEL_TO_ASSISTANT.get(model, "general")
    @staticmethod
    def build_messages(messages: list[dict[str, str]], assistant: str) -> list[dict[str, str]]:
        """Compatibility wrapper; production composition is owned by PromptComposer."""
        return AIRouter._compose_messages(default_prompt_composer(), messages, assistant)

    @staticmethod
    def _compose_messages(composer, messages: list[dict[str, str]], assistant: str) -> list[dict[str, str]]:
        filtered = [message for message in messages if message.get("role") != "system"]
        if filtered:
            final, history = filtered[-1], filtered[:-1]
            user_input, final_role = final.get("content", ""), final.get("role", "")
            final_metadata = tuple((key, value) for key, value in final.items() if key not in {"role", "content"} and isinstance(value, str))
        else:
            history, user_input, final_role, final_metadata = [], "", "user", ()
        history_messages = tuple(PromptMessage(item.get("role", ""), item.get("content", ""), tuple((key, value) for key, value in item.items() if key not in {"role", "content"} and isinstance(value, str))) for item in history)
        result = composer.compose(PromptCompositionRequest(user_input, conversation_history=history_messages, final_role=final_role, final_metadata=final_metadata, include_final_message=bool(filtered), assistant=assistant))
        return [message.to_dict() for message in result.messages]

    async def _execute_legacy(self, messages: list[dict[str, str]]) -> str:
        # Preserve the legacy invocation, including its service-default model selection.
        return await self._ollama.chat(messages)

    async def _execute_via_runtime(self, messages: list[dict[str, str]], model: str) -> str:
        try:
            runtime_messages = tuple(RuntimeMessage(message["role"], message["content"]) for message in messages)
        except (KeyError, TypeError, ValueError) as exc:
            raise OllamaServiceError("Model inference request is invalid.") from exc
        execution_id = f"runtime-{uuid4()}"
        plan = ExecutionPlan(execution_id, execution_id, "chat", "local-ollama-v1", model, "ollama", timeout_ms=int(settings.request_timeout_seconds * 1000), max_retries=0)
        started = monotonic()
        if self._runtime is None:
            self._runtime = build_local_ollama_runtime(self._ollama)
        runtime = self._runtime
        result = await runtime.execute(RuntimeRequest(execution_id, plan, runtime_messages))
        self._record_runtime_trace(result, model, int((monotonic() - started) * 1000))
        if result.status is RuntimeStatus.SUCCEEDED and result.output is not None:
            return result.output
        self._raise_runtime_error(result.status, result.attempts[-1].error_code if result.attempts else None)

    @staticmethod
    def _raise_runtime_error(status: RuntimeStatus, code: str | None) -> None:
        if status is RuntimeStatus.CANCELLED: raise OllamaServiceError()
        if status is RuntimeStatus.TIMED_OUT or code == "timeout": raise OllamaInferenceTimeoutError()
        if code == "empty-output": raise OllamaEmptyResponseError()
        if code == "truncated-output": raise OllamaTruncatedResponseError()
        if code == "malformed-response": raise OllamaMalformedResponseError()
        if code == "upstream-error": raise OllamaUpstreamError()
        raise OllamaServiceError()

    @staticmethod
    def _record_runtime_trace(result, model: str, duration_ms: int) -> None:
        stats, usage = dict(result.statistics), {}
        trace = RuntimeExecutionTrace(result.execution_id, result.plan_id, model, result.completed_adapter_id, "ollama", "local", duration_ms, result.status.value, "completed" if result.status is RuntimeStatus.SUCCEEDED else result.status.value, usage.get("prompt_eval_count"), usage.get("eval_count"), sum(item.retry_index > 0 for item in result.attempts), stats.get("fallback_count", 0), result.diagnostics)
        logger.info("ai_runtime.execution %s", trace)

    async def chat(self, message: str, assistant: AssistantName, *, user_identifier: str | None = None) -> str:
        messages = self._compose_messages(self._prompt_composer, [{"role": "user", "content": message}], assistant)
        production_prompt = production_prompt_from_messages(messages)
        routed_messages, _, _ = await self._shadow_service.route_messages(messages=messages, request_id=shadow_request_id(production_prompt), user_identifier=user_identifier, intent=f"chat_{assistant}")
        # Legacy currently uses the service default model and no retry/fallback policy.
        model = settings.ollama_model
        if not self._runtime_enabled:
            return await self._execute_legacy(routed_messages)
        return await self._execute_via_runtime(routed_messages, model)


ai_router = AIRouter()
