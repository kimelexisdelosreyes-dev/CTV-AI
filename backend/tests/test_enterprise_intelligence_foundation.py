import json
from dataclasses import FrozenInstanceError
import pytest
from app.enterprise_intelligence import *
from app.enterprise_intelligence.diagnostics import EnterpriseIntelligenceTrace
def test_contracts_managers_policies_and_serialization():
 k=KnowledgeItem("k","Title","text","document",relevance=.8); m=MemoryItem("m","user","memory",.9)
 assert KnowledgeManager().validate(KnowledgeContext((k,))).items==(k,)
 assert MemoryManager().validate(MemoryContext((m,))).items==(m,)
 assert json.dumps(RetrievalResult(KnowledgeContext((k,)),MemoryContext((m,))).to_dict())
 assert KnowledgePolicy().require_source_id and MemoryPolicy().minimum_confidence==0 and RankingPolicy().preserve_input_order
 assert EnterpriseIntelligenceTrace("knowledge","default",1,0).item_count==1
 with pytest.raises(FrozenInstanceError): k.title="x"
 with pytest.raises(TypeError): MemoryItem("m","s","x",2)
