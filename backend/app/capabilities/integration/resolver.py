class CapabilityResolver:
 def resolve(self,metadata): return dict(metadata or ()).get("capability_id")
