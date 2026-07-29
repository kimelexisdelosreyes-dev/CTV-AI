from app.api.v1.capabilities.schemas import CapabilityExecutionRequest
from app.api.v1.capabilities.service import CapabilityRequestService
from app.core.config import settings
def test_explicit_execution_preserves_request_id(monkeypatch):
 monkeypatch.setattr(settings,"ctv_one_capability_api_enabled",True);monkeypatch.setattr(settings,"ctv_one_capability_framework_enabled",True)
 result,trace=CapabilityRequestService().execute(CapabilityExecutionRequest(capability_id="company-brain",request_id="r"));assert result.status=="succeeded" and trace
