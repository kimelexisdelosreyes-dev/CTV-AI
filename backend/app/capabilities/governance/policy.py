from dataclasses import dataclass
class CapabilityHealthPolicy:
 def evaluate(self,health): return health.healthy
class CapabilityLifecyclePolicy:
 def allows(self,state): return state.value in {"registered","validated","available","disabled","deprecated"}
class CapabilityVersionPolicy:
 def validate(self,version): return bool(version and isinstance(version,str))
