from .contracts import AdapterDescriptor, AdapterResult, RuntimeStatus
class DeterministicTestAdapter:
    descriptor=AdapterDescriptor("deterministic-test","internal",("test-model",),priority=0)
    def supports(self,**request):return request["model_id"]=="test-model" and request["provider_type"]=="internal"
    async def execute(self,*,execution_id,model_id,messages,cancelled=None):
        if cancelled and cancelled.is_set():return AdapterResult(RuntimeStatus.CANCELLED,self.descriptor.adapter_id,model_id,error_code="cancelled")
        return AdapterResult(RuntimeStatus.SUCCEEDED,self.descriptor.adapter_id,model_id,output="deterministic-test-output")
