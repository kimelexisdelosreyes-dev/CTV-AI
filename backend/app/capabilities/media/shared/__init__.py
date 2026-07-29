from dataclasses import asdict,dataclass
from app.capabilities.execution import CapabilityHandler,CapabilityHandlerResult
@dataclass(frozen=True)
class CapabilityProfile:
 capability_id:str; name:str; description:str; category:str; supported_inputs:tuple[str,...]; supported_outputs:tuple[str,...]; required_enterprise_context:tuple[str,...]=(); preferred_models:tuple[str,...]=(); estimated_cost:str="unknown"; expected_latency:str="unknown"; permissions:tuple[str,...]=(); version:str="1.0"
 def to_dict(self): return asdict(self)
class MediaHandler(CapabilityHandler):
 def execute(self,context): return CapabilityHandlerResult("succeeded",(("capability_id",context.request.capability_id),("output_kind",self.output_kind)))
