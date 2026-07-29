from dataclasses import asdict, dataclass
from app.enterprise_intelligence.contracts import KnowledgeContext, MemoryContext
@dataclass(frozen=True)
class SelectionResult: knowledge:KnowledgeContext; memory:MemoryContext
@dataclass(frozen=True)
class BudgetResult: remaining_budget:int; consumed_budget:int; truncated:bool
@dataclass(frozen=True)
class ContextFilterResult: included:tuple; excluded:tuple; reason:str
@dataclass(frozen=True)
class PolicyDecision:
 selected_knowledge:KnowledgeContext; selected_memory:MemoryContext; rejected_knowledge:tuple=(); rejected_memory:tuple=(); warnings:tuple[str,...]=(); diagnostics:tuple[str,...]=()
 def to_dict(self): return asdict(self)
