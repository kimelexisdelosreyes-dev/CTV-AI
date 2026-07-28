from typing import Protocol, Sequence
class OllamaTransport(Protocol):
    async def chat(self, messages:list[dict[str,str]], model:str|None=None, return_metadata:bool=False)->str|tuple[str,dict[str,object]]: ...
class ExistingOllamaServiceTransport:
    def __init__(self, service:OllamaTransport)->None:self._service=service
    async def chat(self, *, model:str, messages:list[dict[str,str]])->str|tuple[str,dict[str,object]]:return await self._service.chat(messages,model=model,return_metadata=True)
