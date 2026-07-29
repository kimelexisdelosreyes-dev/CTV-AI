class CapabilityRegistry:
 def __init__(self): self._items={};self._manifests={};self._handlers={};self._governance={}
 def register(self,definition):
  if not definition.id or definition.id in self._items: raise ValueError("duplicate or missing capability id")
  self._items[definition.id]=definition
 def register_operational(self,definition,manifest,handler,governance):
  if manifest.capability_id!=definition.id or not handler or not governance: raise ValueError("invalid operational capability")
  self.register(definition);self._manifests[definition.id]=manifest;self._handlers[definition.id]=handler;self._governance[definition.id]=governance
 def validate_startup(self):
  missing=tuple(key for key in sorted(self._items) if key not in self._manifests or key not in self._handlers or key not in self._governance)
  if missing: raise ValueError("missing operational registration: "+",".join(missing))
  return tuple((key,"valid") for key in sorted(self._items))
 def get(self,capability_id): return self._items.get(capability_id)
 def list(self): return tuple(self._items[key] for key in sorted(self._items))
