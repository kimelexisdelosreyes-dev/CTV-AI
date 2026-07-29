from dataclasses import asdict, dataclass
from enum import StrEnum


class PromptRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class PromptMessage:
    role: str
    content: str
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.role, str) or not isinstance(self.content, str):
            raise TypeError("message role and content must be strings")
        if not isinstance(self.metadata, tuple) or not all(isinstance(pair, tuple) and len(pair) == 2 and all(isinstance(value, str) for value in pair) for pair in self.metadata):
            raise TypeError("message metadata must be immutable string pairs")

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content, **dict(self.metadata)}


@dataclass(frozen=True)
class PromptCompositionResult:
    composition_id: str
    logical_prompt: tuple[PromptMessage, ...]
    messages: tuple[PromptMessage, ...]
    metadata: tuple[tuple[str, str], ...]
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
