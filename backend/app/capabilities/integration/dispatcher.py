class CapabilityDispatcher:
 def __init__(self,resolver,mapper,router,executor,handlers,gate): self.resolver=resolver;self.mapper=mapper;self.router=router;self.executor=executor;self.handlers=handlers;self.gate=gate
 def dispatch(self,metadata=()):
  if not self.gate.enabled(): return None
  capability_id=self.resolver.resolve(metadata)
  if not capability_id:return None
  request=self.mapper.map(capability_id,metadata); plan=self.router.plan(request)
  from app.capabilities.execution import ExecutionContext
  return self.executor.execute(plan,ExecutionContext(request))
