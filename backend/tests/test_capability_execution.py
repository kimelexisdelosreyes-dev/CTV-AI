import pytest
from app.capabilities import CapabilityDefinition,CapabilityRegistry,CapabilityRequest
from app.capabilities.execution import *
def test_routing_execution_and_unknown_capability():
 r=CapabilityRegistry();r.register(CapabilityDefinition("echo","Echo","","test","1")); request=CapabilityRequest("echo",(("x","y"),))
 plan=CapabilityRouter(r).plan(request); result=CapabilityExecutor({"echo":EchoCapabilityHandler()}).execute(plan,ExecutionContext(request))
 assert result.status=="succeeded" and result.metadata==(("capability_id","echo"),)
 with pytest.raises(ValueError):CapabilityRouter(r).plan(CapabilityRequest("missing"))
