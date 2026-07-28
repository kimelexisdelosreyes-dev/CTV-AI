import asyncio
from app.ai_runtime.adapters.ollama.adapter import OllamaModelAdapter
from app.ai_runtime.adapters.ollama.transport import ExistingOllamaServiceTransport
from app.ai_runtime.contracts import RuntimeStatus
class MockService:
 def __init__(self):self.calls=[]
 async def chat(self,messages,model=None,return_metadata=False):self.calls.append((messages,model,return_metadata));return ("answer",{"prompt_eval_count":2,"eval_count":3})
def test_ollama_adapter_preserves_model_and_normalizes_response():
 service=MockService();adapter=OllamaModelAdapter(ExistingOllamaServiceTransport(service));model=adapter.descriptor.model_ids[0];result=asyncio.run(adapter.execute(execution_id="x",model_id=model,content="exact prompt"));assert result.status is RuntimeStatus.SUCCEEDED;assert service.calls==[([{"role":"user","content":"exact prompt"}],model,True)];assert dict(result.usage)["total_tokens"]==5
def test_ollama_adapter_cancellation_does_not_call_transport():
 service=MockService();adapter=OllamaModelAdapter(ExistingOllamaServiceTransport(service));event=asyncio.Event();event.set();result=asyncio.run(adapter.execute(execution_id="x",model_id=adapter.descriptor.model_ids[0],content="x",cancelled=event));assert result.status is RuntimeStatus.CANCELLED and not service.calls
