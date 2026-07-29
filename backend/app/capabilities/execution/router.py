from .plan import ExecutionPlan
class CapabilityRouter:
 def __init__(self,registry): self._registry=registry
 def plan(self,request):
  if not self._registry.get(request.capability_id): raise ValueError("unknown capability")
  return ExecutionPlan(request.capability_id,request.request_context,request.parameters)
