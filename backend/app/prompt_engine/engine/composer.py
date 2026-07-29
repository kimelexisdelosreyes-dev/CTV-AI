import hashlib
import json
from time import monotonic

from app.prompt_engine.contracts import PromptCompositionContext, PromptCompositionRequest, PromptCompositionResult
from app.prompt_engine.diagnostics import CompositionStatistics, CompositionTrace

from .registry import PromptStageRegistry


class PromptComposer:
    def __init__(self, registry: PromptStageRegistry) -> None:
        self._registry = registry
        self.last_trace: CompositionTrace | None = None
        self.last_statistics: CompositionStatistics | None = None

    def compose(self, request: PromptCompositionRequest) -> PromptCompositionResult:
        started = monotonic()
        context = PromptCompositionContext(request)
        for stage in self._registry.stages:
            context = stage.compose(context)
        duration_ms = int((monotonic() - started) * 1000)
        identity = json.dumps([message.to_dict() for message in context.logical_messages], separators=(",", ":"), ensure_ascii=False)
        composition_id = f"prompt-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"
        self.last_trace = CompositionTrace(composition_id, self._registry.stage_ids, duration_ms, tuple(context.warnings))
        self.last_statistics = CompositionStatistics(len(self._registry.stages), duration_ms, len(context.warnings))
        messages = tuple(context.logical_messages)
        return PromptCompositionResult(composition_id, messages, messages, request.metadata, tuple(context.warnings))


def default_prompt_composer() -> PromptComposer:
    from app.prompt_engine.stages import ConversationStage, EnterpriseContextStage, ProviderFormattingStage, SystemPromptStage
    return PromptComposer(PromptStageRegistry((SystemPromptStage(), EnterpriseContextStage(), ConversationStage(), ProviderFormattingStage())))
