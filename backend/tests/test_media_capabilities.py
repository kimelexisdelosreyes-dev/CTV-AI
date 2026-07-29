from app.capabilities import CapabilityRegistry
from app.capabilities.media import register_media_capabilities
def test_media_capabilities_register():
 r=CapabilityRegistry();assert len(register_media_capabilities(r))==4 and len(r.list())==4
