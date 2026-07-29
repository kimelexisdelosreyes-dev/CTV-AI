from app.capabilities import CapabilityRequest
class CapabilityContextMapper:
 def map(self,capability_id,metadata=()): return CapabilityRequest(capability_id,request_context=tuple(metadata))
