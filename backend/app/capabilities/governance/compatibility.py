from dataclasses import dataclass
@dataclass(frozen=True)
class CapabilityCompatibilityPolicy:
 def validate(self,metadata): return bool(metadata.version)
