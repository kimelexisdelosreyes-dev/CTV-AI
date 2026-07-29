import json
from app.capabilities.media.shared import CapabilityProfile
def test_profile_is_serializable(): assert json.dumps(CapabilityProfile("x","X","d","media",("text",),("plan",)).to_dict())
