import pytest
from app.api.v1.capabilities.schemas import CapabilityExecutionRequest
from app.api.v1.capabilities.service import CapabilityRequestService
from app.core.config import settings
def test_framework_disabled_and_unknown_are_safe(monkeypatch):
 monkeypatch.setattr(settings,"ctv_one_capability_api_enabled",True);monkeypatch.setattr(settings,"ctv_one_capability_framework_enabled",False)
 with pytest.raises(ValueError,match="CAPABILITY_FRAMEWORK_DISABLED"): CapabilityRequestService().execute(CapabilityExecutionRequest(capability_id="secret"))
