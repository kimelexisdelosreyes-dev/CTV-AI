from .health import CapabilityHealth
from .lifecycle import CapabilityLifecycle
from .metadata import CapabilityMetadata
from .compatibility import CapabilityCompatibilityPolicy
from .policy import CapabilityHealthPolicy, CapabilityLifecyclePolicy, CapabilityVersionPolicy
class CapabilityGovernanceManager:
 def validate(self,lifecycle,metadata,health):
  if not CapabilityLifecyclePolicy().allows(lifecycle) or not CapabilityVersionPolicy().validate(metadata.version): raise ValueError("invalid capability governance")
  return CapabilityCompatibilityPolicy().validate(metadata) and CapabilityHealthPolicy().evaluate(health)
