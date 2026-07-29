from app.enterprise_intelligence.integration import EnterpriseIntegrationCoordinator, KnowledgeAdapter, MemoryAdapter
def test_adapters_and_coordinator_preserve_order_and_empty_memory():
 knowledge=KnowledgeAdapter().adapt(({"id":"a","title":"A","content":"one"},{"id":"b","title":"B","content":"two"}))
 assert [x.source_id for x in knowledge.items]==["a","b"] and MemoryAdapter().adapt(None).items==()
 result=EnterpriseIntegrationCoordinator().integrate(knowledge_results=knowledge.items)
 assert len(result.knowledge.items)==2 and result.memory.items==() and result.diagnostics==("knowledge-items:2","memory-items:0")
