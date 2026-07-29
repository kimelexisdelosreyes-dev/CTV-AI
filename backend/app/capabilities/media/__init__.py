from app.capabilities import CapabilityDefinition
from .shared import CapabilityProfile
from .firefly_prompt import FireflyPromptCapabilityHandler
from .documentary_research import DocumentaryResearchCapabilityHandler
from .archive_restoration import ArchiveRestorationCapabilityHandler
from .production_planner import ProductionPlannerCapabilityHandler
def register_media_capabilities(registry):
 items=(("firefly-prompt","Firefly Prompt Studio",FireflyPromptCapabilityHandler),("documentary-research","Documentary Research",DocumentaryResearchCapabilityHandler),("archive-restoration","Archive Restoration",ArchiveRestorationCapabilityHandler),("production-planner","Production Planner",ProductionPlannerCapabilityHandler))
 for key,name,handler in items: registry.register(CapabilityDefinition(key,name,"Provider-neutral media capability","media","1.0"))
 return {key:handler() for key,name,handler in items}
