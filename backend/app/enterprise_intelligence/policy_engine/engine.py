from app.enterprise_intelligence.contracts import ContextBudget, KnowledgeContext, MemoryContext, RetrievalResult
from .decision import PolicyDecision
from .selectors import KnowledgeSelectionPolicy, MemorySelectionPolicy, SourcePriorityPolicy
class EnterprisePolicyEngine:
 def evaluate(self,result:RetrievalResult,budget:ContextBudget=ContextBudget()):
  knowledge=tuple(KnowledgeSelectionPolicy().select(SourcePriorityPolicy().order(result.knowledge.items)))[:budget.max_knowledge_items]; memory=tuple(MemorySelectionPolicy().select(result.memory.items))[:budget.max_memory_items]
  return PolicyDecision(KnowledgeContext(knowledge),MemoryContext(memory),result.knowledge.items[len(knowledge):],result.memory.items[len(memory):],(),(f"knowledge-selected:{len(knowledge)}",f"memory-selected:{len(memory)}"))
