from dataclasses import dataclass, field

from .request import PromptCompositionRequest
from .result import PromptMessage


@dataclass
class PromptCompositionContext:
    """Engine-private mutable state; never returned or logged."""
    request: PromptCompositionRequest
    logical_messages: list[PromptMessage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    enterprise_diagnostics: list[str] = field(default_factory=list)
