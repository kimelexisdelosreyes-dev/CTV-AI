from abc import ABC,abstractmethod
from dataclasses import dataclass
@dataclass(frozen=True)
class CapabilityHandlerResult: status:str; metadata:tuple[tuple[str,str],...]=(); warnings:tuple[str,...]=(); output_reference:str|None=None
class CapabilityHandler(ABC):
 def validate(self,context): return context
 def prepare(self,context): return context
 @abstractmethod
 def execute(self,context): ...
 def cleanup(self): pass
class EchoCapabilityHandler(CapabilityHandler):
 def execute(self,context): return CapabilityHandlerResult("succeeded",(("capability_id",context.request.capability_id),))
