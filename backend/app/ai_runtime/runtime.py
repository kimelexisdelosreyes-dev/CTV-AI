import asyncio
from .contracts import AdapterResult, AttemptStatus, ExecutionAttempt, ExecutionPlan, RuntimeResult, RuntimeStatus
from .registry import AIModelAdapterRegistry
class AIModelRuntime:
    def __init__(self,registry:AIModelAdapterRegistry)->None:self._registry=registry
    async def execute(self,*,execution_id:str,plan:ExecutionPlan,content:str,cancelled:asyncio.Event|None=None)->RuntimeResult:
        attempts:list[ExecutionAttempt]=[]; diagnostics:list[str]=[]; sequence=(plan.model_id,*plan.fallback_model_ids)
        for fallback_index,model_id in enumerate(sequence):
            retries=0
            while retries<=plan.max_retries:
                if cancelled and cancelled.is_set(): return self._result(execution_id,plan,RuntimeStatus.CANCELLED,None,None,None,attempts,diagnostics+["cancelled"])
                adapter=self._registry.resolve(model_id=model_id,provider_type=plan.provider_type,location=plan.location,mode=plan.mode); attempt_id=f"{execution_id}:attempt:{len(attempts)+1}"
                if not adapter: attempts.append(ExecutionAttempt(attempt_id,len(attempts)+1,model_id,None,AttemptStatus.INCOMPATIBLE,retries,fallback_index));diagnostics.append("adapter-unavailable");break
                try: result=await asyncio.wait_for(adapter.execute(execution_id=execution_id,model_id=model_id,content=content,cancelled=cancelled),timeout=plan.timeout_ms/1000)
                except TimeoutError: result=AdapterResult(RuntimeStatus.TIMED_OUT,adapter.descriptor.adapter_id,model_id,error_code="timeout",error_category="timeout",fallback_eligible=True)
                status=AttemptStatus.SUCCEEDED if result.status is RuntimeStatus.SUCCEEDED else AttemptStatus.TIMED_OUT if result.status is RuntimeStatus.TIMED_OUT else AttemptStatus.CANCELLED if result.status is RuntimeStatus.CANCELLED else AttemptStatus.FAILED
                attempts.append(ExecutionAttempt(attempt_id,len(attempts)+1,model_id,adapter.descriptor.adapter_id,status,retries,fallback_index,result.error_code))
                if result.status is RuntimeStatus.SUCCEEDED:return self._result(execution_id,plan,RuntimeStatus.SUCCEEDED,result.output,model_id,adapter.descriptor.adapter_id,attempts,diagnostics)
                if result.status is RuntimeStatus.CANCELLED:return self._result(execution_id,plan,RuntimeStatus.CANCELLED,None,None,None,attempts,diagnostics)
                if result.retryable and retries<plan.max_retries: retries+=1;continue
                if not result.fallback_eligible:return self._result(execution_id,plan,result.status,None,None,None,attempts,diagnostics)
                break
        return self._result(execution_id,plan,RuntimeStatus.FAILED,None,None,None,attempts,diagnostics)
    @staticmethod
    def _result(execution_id,plan,status,output,model,adapter,attempts,diagnostics):return RuntimeResult(execution_id,status,plan.plan_id,plan.fingerprint,output,model,adapter,tuple(attempts),tuple(diagnostics),(("attempt_count",len(attempts)),("fallback_count",sum(a.fallback_index>0 for a in attempts))),(("registry_version",plan.registry_version),))
