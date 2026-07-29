from dataclasses import asdict, dataclass
from .knowledge import KnowledgeContext
from .memory import MemoryContext
@dataclass(frozen=True)
class RetrievalResult:
 knowledge:KnowledgeContext=KnowledgeContext(); memory:MemoryContext=MemoryContext(); diagnostics:tuple[str,...]=()
 def to_dict(self): return asdict(self)
