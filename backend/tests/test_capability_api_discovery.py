from app.api.v1.capabilities.service import CapabilityRequestService
def test_registry_discovery_is_deterministic_and_safe():
 items=CapabilityRequestService().list(); assert [x.id for x in items]==sorted(x.id for x in items) and all("Handler" not in x.name for x in items)
