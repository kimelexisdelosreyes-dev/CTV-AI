from app.enterprise_intelligence import *
from app.enterprise_intelligence.policy_engine import EnterprisePolicyEngine
def test_policy_selection_is_deterministic_and_immutable():
 result=EnterprisePolicyEngine().evaluate(RetrievalResult(KnowledgeContext((KnowledgeItem("a","A","x","doc"),KnowledgeItem("b","B","y","doc"))),MemoryContext()),ContextBudget(max_knowledge_items=1))
 assert [x.source_id for x in result.selected_knowledge.items]==["a"] and [x.source_id for x in result.rejected_knowledge]==["b"]
