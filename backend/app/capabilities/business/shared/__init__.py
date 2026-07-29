from app.capabilities.execution import CapabilityHandler, CapabilityHandlerResult
class MetadataCapabilityHandler(CapabilityHandler):
 def execute(self,context): return CapabilityHandlerResult("succeeded",(("capability_id",context.request.capability_id),("output_kind",self.output_kind)))
