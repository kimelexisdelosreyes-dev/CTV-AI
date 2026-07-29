import pytest
from app.capabilities.governance import *
def test_governance_lifecycle_metadata_and_health():
 m=CapabilityMetadata("CTV","1","now","now"); h=CapabilityHealth(True)
 assert CapabilityGovernanceManager().validate(CapabilityLifecycle.AVAILABLE,m,h)
 with pytest.raises(ValueError):CapabilityGovernanceManager().validate(CapabilityLifecycle.AVAILABLE,CapabilityMetadata("x","","n","n"),h)
