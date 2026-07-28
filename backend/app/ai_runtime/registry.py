from .contracts import AdapterDescriptor, ModelAdapter
class AIModelAdapterRegistry:
    def __init__(self)->None: self._adapters:dict[str,ModelAdapter]={}
    def register(self,adapter:ModelAdapter)->None:
        if not adapter.descriptor.adapter_id or adapter.descriptor.adapter_id in self._adapters: raise ValueError("duplicate adapter id")
        self._adapters[adapter.descriptor.adapter_id]=adapter
    def snapshot(self)->tuple[AdapterDescriptor,...]: return tuple(sorted((a.descriptor for a in self._adapters.values()),key=lambda d:d.adapter_id))
    def resolve(self,*,model_id:str,provider_type:str,location:str,mode:str)->ModelAdapter|None:
        matches=[a for a in self._adapters.values() if a.descriptor.enabled and a.supports(model_id=model_id,provider_type=provider_type,location=location,mode=mode)]
        return next(iter(sorted(matches,key=lambda a:(-a.descriptor.priority,a.descriptor.adapter_id))),None)
