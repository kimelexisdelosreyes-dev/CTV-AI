from app.enterprise_intelligence.contracts import KnowledgeContext
class KnowledgeManager:
 def validate(self, context:KnowledgeContext)->KnowledgeContext: return KnowledgeContext(tuple(context.items))
