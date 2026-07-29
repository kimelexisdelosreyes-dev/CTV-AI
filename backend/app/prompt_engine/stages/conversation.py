from app.prompt_engine.contracts import PromptCompositionContext, PromptMessage, PromptRole, PromptStage


class ConversationStage(PromptStage):
    stage_id = "conversation"

    def compose(self, context: PromptCompositionContext) -> PromptCompositionContext:
        context.logical_messages.extend(context.request.conversation_history)
        if context.request.include_final_message:
            context.logical_messages.append(PromptMessage(context.request.final_role, context.request.user_input, context.request.final_metadata))
        return context
