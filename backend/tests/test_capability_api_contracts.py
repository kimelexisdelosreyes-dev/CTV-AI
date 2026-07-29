from app.api.v1.capabilities.schemas import CapabilityExecutionRequest
def test_explicit_capability_contract(): assert CapabilityExecutionRequest(capability_id="echo").capability_id=="echo"
