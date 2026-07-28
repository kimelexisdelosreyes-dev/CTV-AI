import asyncio
from dataclasses import replace
from app.core.config import settings
from app.ai_runtime.contracts import AdapterDescriptor, AdapterResult, RuntimeStatus
from .transport import ExistingOllamaServiceTransport
def configured_models()->tuple[str,...]:return tuple(sorted({str(x) for x in (settings.ctv_one_model_fast,settings.ctv_one_model_balanced,settings.ctv_one_model_reasoning,settings.ctv_one_model_operations,settings.ctv_one_model_knowledge,settings.ctv_one_model_default) if x}))
class OllamaModelAdapter:
    descriptor=AdapterDescriptor("ollama-local","ollama",configured_models(),priority=100)
    def __init__(self,transport:ExistingOllamaServiceTransport)->None:self._transport=transport
    def supports(self,*,model_id:str,provider_type:str,location:str,mode:str)->bool:return self.descriptor.enabled and provider_type=="ollama" and location=="local" and mode=="synchronous" and model_id in self.descriptor.model_ids
    async def execute(self,*,execution_id:str,model_id:str,content:str,cancelled:asyncio.Event|None=None)->AdapterResult:
        if cancelled and cancelled.is_set():return AdapterResult(RuntimeStatus.CANCELLED,self.descriptor.adapter_id,model_id,error_code="cancelled",error_category="cancellation")
        if not content:return AdapterResult(RuntimeStatus.FAILED,self.descriptor.adapter_id,model_id,error_code="invalid-input",error_category="validation")
        try:
            response=await self._transport.chat(model=model_id,messages=[{"role":"user","content":content}])
            if cancelled and cancelled.is_set():return AdapterResult(RuntimeStatus.CANCELLED,self.descriptor.adapter_id,model_id,error_code="cancelled",error_category="cancellation")
            text,metadata=response if isinstance(response,tuple) else (response,{})
            if not isinstance(text,str) or not text.strip():return AdapterResult(RuntimeStatus.FAILED,self.descriptor.adapter_id,model_id,error_code="empty-output",error_category="malformed-response",fallback_eligible=True)
            usage=tuple((key,int(metadata[key])) for key in ("prompt_eval_count","eval_count") if isinstance(metadata.get(key),int) and metadata[key]>=0)
            if len(usage)==2:usage=(*usage,("total_tokens",usage[0][1]+usage[1][1]))
            return AdapterResult(RuntimeStatus.SUCCEEDED,self.descriptor.adapter_id,model_id,output=text,usage=usage)
        except asyncio.CancelledError:return AdapterResult(RuntimeStatus.CANCELLED,self.descriptor.adapter_id,model_id,error_code="cancelled",error_category="cancellation")
        except TimeoutError:return AdapterResult(RuntimeStatus.TIMED_OUT,self.descriptor.adapter_id,model_id,error_code="timeout",error_category="timeout",retryable=True,fallback_eligible=True)
        except Exception:return AdapterResult(RuntimeStatus.FAILED,self.descriptor.adapter_id,model_id,error_code="ollama-transport",error_category="transport",retryable=True,fallback_eligible=True)
