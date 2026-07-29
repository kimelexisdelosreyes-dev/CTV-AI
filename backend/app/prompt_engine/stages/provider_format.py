from app.prompt_engine.contracts import PromptCompositionContext, PromptStage


class ProviderFormattingStage(PromptStage):
    """Creates provider-neutral message values only; no provider payload is formed."""
    stage_id = "provider-format"

    def compose(self, context: PromptCompositionContext) -> PromptCompositionContext:
        context.logical_messages[:] = list(context.logical_messages)
        return context
