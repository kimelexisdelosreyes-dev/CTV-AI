from dataclasses import asdict, dataclass


def _pairs(value: tuple[tuple[str, str], ...]) -> bool:
    return isinstance(value, tuple) and all(isinstance(pair, tuple) and len(pair) == 2 and all(isinstance(part, str) for part in pair) for pair in value)


@dataclass(frozen=True)
class EnterpriseContextItem:
    source_id: str
    title: str
    content: str
    relevance: float | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    def __post_init__(self) -> None:
        if not all(isinstance(value, str) for value in (self.source_id, self.title, self.content)) or (self.relevance is not None and not isinstance(self.relevance, (int, float))) or not _pairs(self.metadata):
            raise TypeError("enterprise context item is invalid")


@dataclass(frozen=True)
class EnterpriseContext:
    company_brain: tuple[EnterpriseContextItem, ...] = ()
    knowledge: tuple[EnterpriseContextItem, ...] = ()
    def __post_init__(self) -> None:
        if not isinstance(self.company_brain, tuple) or not isinstance(self.knowledge, tuple) or not all(isinstance(item, EnterpriseContextItem) for item in (*self.company_brain, *self.knowledge)):
            raise TypeError("enterprise context sources must be immutable item tuples")
    def to_dict(self) -> dict[str, object]: return asdict(self)
