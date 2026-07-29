from app.capabilities import CapabilityDefinition,CapabilityRegistry
from app.capabilities.execution import CapabilityExecutor,CapabilityRouter,EchoCapabilityHandler
from app.capabilities.integration import *
from app.core.config import settings
def test_dispatcher_disabled_then_enabled(monkeypatch):
 r=CapabilityRegistry();r.register(CapabilityDefinition("echo","E","","x","1"));d=CapabilityDispatcher(CapabilityResolver(),CapabilityContextMapper(),CapabilityRouter(r),CapabilityExecutor({"echo":EchoCapabilityHandler()}),{},CapabilityFeatureGate())
 assert d.dispatch((("capability_id","echo"),)) is None
 monkeypatch.setattr(settings,"ctv_one_capability_framework_enabled",True);assert d.dispatch((("capability_id","echo"),)).status=="succeeded"
