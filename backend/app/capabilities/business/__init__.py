from app.capabilities import CapabilityDefinition
from .company_brain import CompanyBrainCapabilityHandler
from .hr_policy import HRPolicyCapabilityHandler
from .meeting_summary import MeetingSummaryCapabilityHandler
from .document_analysis import DocumentAnalysisCapabilityHandler
def register_business_capabilities(registry):
 items=(("company-brain","Company Brain",CompanyBrainCapabilityHandler),("hr-policy","HR Policy",HRPolicyCapabilityHandler),("meeting-summary","Meeting Summary",MeetingSummaryCapabilityHandler),("document-analysis","Document Analysis",DocumentAnalysisCapabilityHandler))
 for key,name,handler in items: registry.register(CapabilityDefinition(key,name,"Framework-native business capability","business","1.0"))
 return {key:handler() for key,name,handler in items}
