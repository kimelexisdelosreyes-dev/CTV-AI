from dataclasses import dataclass

from .result import PromptMessage
from .enterprise import EnterpriseContext


@dataclass(frozen=True)
class PromptCompositionRequest:
    """Provider-neutral input; no runtime, transport, or HTTP objects are accepted."""
    user_input: str
    conversation_history: tuple[PromptMessage, ...] = ()
    selected_model_id: str = ""
    enterprise_context: EnterpriseContext | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    final_role: str = "user"
    final_metadata: tuple[tuple[str, str], ...] = ()
    include_final_message: bool = True
    assistant: str = "general"

    def __post_init__(self) -> None:
        if not isinstance(self.user_input, str):
            raise TypeError("user_input must be a string")
        if not isinstance(self.final_role, str) or not isinstance(self.assistant, str):
            raise TypeError("final_role and assistant must be strings")
        if not isinstance(self.final_metadata, tuple) or not all(isinstance(pair, tuple) and len(pair) == 2 and all(isinstance(value, str) for value in pair) for pair in self.final_metadata):
            raise TypeError("final_metadata must be immutable string pairs")
        if not isinstance(self.conversation_history, tuple):
            raise TypeError("conversation_history must be an immutable tuple")
        if not all(isinstance(item, PromptMessage) for item in self.conversation_history):
            raise TypeError("conversation_history must contain PromptMessage values")
        if not isinstance(self.selected_model_id, str):
            raise TypeError("selected_model_id must be a string")
        if self.enterprise_context is not None and not isinstance(self.enterprise_context, EnterpriseContext):
            raise TypeError("enterprise_context must be EnterpriseContext or None")
        if not isinstance(self.metadata, tuple) or not all(isinstance(pair, tuple) and len(pair) == 2 and all(isinstance(value, str) for value in pair) for pair in self.metadata):
            raise TypeError("metadata must be immutable string pairs")
