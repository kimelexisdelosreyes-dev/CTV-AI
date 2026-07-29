import pytest
from app.api.v1.capabilities.schemas import CapabilityExecutionRequest
from app.api.v1.capabilities.service import CapabilityRequestService
from app.core.config import settings
def test_default_flags_block_execution(monkeypatch):
 monkeypatch.setattr(settings,"ctv_one_capability_api_enabled",False)
 with pytest.raises(ValueError,match="CAPABILITY_API_DISABLED"): CapabilityRequestService().execute(CapabilityExecutionRequest(capability_id="company-brain"))
