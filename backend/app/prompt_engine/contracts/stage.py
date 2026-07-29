from abc import ABC, abstractmethod

from .context import PromptCompositionContext


class PromptStage(ABC):
    stage_id: str

    @abstractmethod
    def compose(self, context: PromptCompositionContext) -> PromptCompositionContext:
        """Mutate only the private composition context and return it."""
