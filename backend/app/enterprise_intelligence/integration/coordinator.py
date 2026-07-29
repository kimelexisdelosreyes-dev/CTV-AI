from app.enterprise_intelligence.contracts import RetrievalResult
from app.enterprise_intelligence.managers import KnowledgeManager, MemoryManager
from .knowledge_adapter import KnowledgeAdapter
from .memory_adapter import MemoryAdapter
class EnterpriseIntegrationCoordinator:
 def __init__(self,knowledge_adapter=None,memory_adapter=None): self.knowledge_adapter=knowledge_adapter or KnowledgeAdapter(); self.memory_adapter=memory_adapter or MemoryAdapter(); self.knowledge_manager=KnowledgeManager(); self.memory_manager=MemoryManager()
 def integrate(self,*,knowledge_results=(),employee_context=()):
  knowledge=self.knowledge_manager.validate(self.knowledge_adapter.adapt(knowledge_results)); memory=self.memory_manager.validate(self.memory_adapter.adapt(employee_context)); return RetrievalResult(knowledge,memory,(f"knowledge-items:{len(knowledge.items)}",f"memory-items:{len(memory.items)}"))
