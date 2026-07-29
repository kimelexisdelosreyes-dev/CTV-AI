class CapabilityExecutor:
 def __init__(self,handlers): self._handlers=handlers
 def execute(self,plan,context):
  handler=self._handlers.get(plan.capability_id)
  if not handler: raise ValueError("missing capability handler")
  try: return handler.execute(handler.prepare(handler.validate(context)))
  finally: handler.cleanup()
