from pydantic import BaseModel, Field
class CapabilityExecutionRequest(BaseModel):
 capability_id:str=Field(min_length=1,max_length=100); input:dict[str,str]={}; context:dict[str,str]={}; request_id:str|None=None; client_metadata:dict[str,str]={}
class CapabilityExecutionResponse(BaseModel): request_id:str; capability_id:str; status:str; output:dict[str,str]={}; warnings:list[str]=[]; trace_id:str; framework_version:str; capability_version:str
class CapabilitySummaryResponse(BaseModel): capability_id:str; name:str; description:str; category:str; version:str
