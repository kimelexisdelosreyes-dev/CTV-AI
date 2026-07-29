class CapabilityManager:
 def __init__(self,registry): self._registry=registry
 def prepare(self,request):
  definition=self._registry.get(request.capability_id)
  if not definition: raise ValueError("unknown capability")
  return definition,request
