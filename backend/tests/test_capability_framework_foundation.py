import json
import pytest
from app.capabilities import *
from app.capabilities.diagnostics import CapabilityTrace
def test_registry_manager_contracts_and_trace():
 d=CapabilityDefinition("demo","Demo","test","test","1") ; r=CapabilityRegistry();r.register(d)
 assert r.list()==(d,) and CapabilityManager(r).prepare(CapabilityRequest("demo"))[0]==d
 with pytest.raises(ValueError):r.register(d)
 assert json.dumps(CapabilityResult("prepared").to_dict()) and CapabilityTrace("demo","lookup",0).action=="lookup"
