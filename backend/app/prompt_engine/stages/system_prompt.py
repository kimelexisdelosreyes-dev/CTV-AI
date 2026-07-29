from app.core.prompts import ASSISTANT_PROMPTS
from app.prompt_engine.contracts import PromptCompositionContext, PromptMessage, PromptRole, PromptStage


class SystemPromptStage(PromptStage):
    stage_id = "system-prompt"
    def compose(self, context: PromptCompositionContext) -> PromptCompositionContext:
        # This is intentionally the exact legacy expression, including `.strip()`.
        context.logical_messages.insert(0, PromptMessage(PromptRole.SYSTEM, ASSISTANT_PROMPTS[context.request.assistant].strip()))
        return context
