from app.enterprise_intelligence.contracts import MemoryContext
class MemoryManager:
 def validate(self, context:MemoryContext)->MemoryContext: return MemoryContext(tuple(context.items))
