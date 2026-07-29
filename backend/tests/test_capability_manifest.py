import pytest
from app.capabilities import CapabilityDefinition,CapabilityRegistry
from app.capabilities.manifest import CapabilityManifest,CapabilityVisibility
def test_manifest_and_startup_validation_are_deterministic():
 r=CapabilityRegistry();d=CapabilityDefinition("x","X","","test","1");m=CapabilityManifest("x","X","","CTV","support","test","validated",CapabilityVisibility.VISIBLE,"available","off")
 r.register_operational(d,m,object(),object());assert r.validate_startup()==(("x","valid"),)
 r=CapabilityRegistry();r.register(d)
 with pytest.raises(ValueError):r.validate_startup()
