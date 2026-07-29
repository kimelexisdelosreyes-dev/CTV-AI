from app.capabilities import CapabilityRegistry
from app.capabilities.business import register_business_capabilities
def test_business_capabilities_register_deterministically():
 registry=CapabilityRegistry(); handlers=register_business_capabilities(registry)
 assert tuple(sorted(handlers))==("company-brain","document-analysis","hr-policy","meeting-summary") and len(registry.list())==4
