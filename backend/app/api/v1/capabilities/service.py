from uuid import uuid4
from app.capabilities import CapabilityRegistry
from app.capabilities.business import register_business_capabilities
from app.capabilities.media import register_media_capabilities
from app.capabilities.execution import CapabilityExecutor,CapabilityRouter
from app.capabilities.integration import CapabilityDispatcher,CapabilityResolver,CapabilityContextMapper,CapabilityFeatureGate
from app.core.config import settings
from app.capabilities.governance import CapabilityGovernanceManager, CapabilityLifecycle, CapabilityMetadata, CapabilityHealth
class CapabilityRequestService:
 def __init__(self):
  self.registry=CapabilityRegistry(); handlers=register_business_capabilities(self.registry);handlers.update(register_media_capabilities(self.registry));self.dispatcher=CapabilityDispatcher(CapabilityResolver(),CapabilityContextMapper(),CapabilityRouter(self.registry),CapabilityExecutor(handlers),handlers,CapabilityFeatureGate());self.governance={item.id:(CapabilityLifecycle.AVAILABLE,CapabilityMetadata("CTV ONE","1.0","framework","framework",category=item.category),CapabilityHealth(True)) for item in self.registry.list()}
 def list(self): return self.registry.list()
 def execute(self,request):
  if not settings.ctv_one_capability_api_enabled: raise ValueError("CAPABILITY_API_DISABLED")
  if not settings.ctv_one_capability_framework_enabled: raise ValueError("CAPABILITY_FRAMEWORK_DISABLED")
  if not self.registry.get(request.capability_id): raise ValueError("CAPABILITY_NOT_FOUND")
  record=self.governance.get(request.capability_id)
  if not record: raise ValueError("CAPABILITY_UNAVAILABLE")
  if record[0] is CapabilityLifecycle.DISABLED: raise ValueError("CAPABILITY_DISABLED")
  if record[0] is CapabilityLifecycle.DEPRECATED: raise ValueError("CAPABILITY_DEPRECATED")
  if not CapabilityGovernanceManager().validate(*record): raise ValueError("CAPABILITY_UNHEALTHY")
  result=self.dispatcher.dispatch((("capability_id",request.capability_id),));
  if result is None: raise ValueError("CAPABILITY_NOT_FOUND")
  return result,f"cap-{uuid4()}"
