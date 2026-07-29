from fastapi import APIRouter,Depends,HTTPException
from app.api.dependencies import get_current_user
from .schemas import *
from .service import CapabilityRequestService
router=APIRouter(prefix="/capabilities",tags=["capabilities"])
service=CapabilityRequestService()
def fail(code): raise HTTPException(status_code=503 if "DISABLED" in code else 404,detail=code)
@router.get("",response_model=list[CapabilitySummaryResponse])
async def list_capabilities(user=Depends(get_current_user)):
 return [CapabilitySummaryResponse(capability_id=x.id,name=x.name,description=x.description,category=x.category,version=x.version) for x in service.list()]
@router.get("/{capability_id}",response_model=CapabilitySummaryResponse)
async def get_capability(capability_id:str,user=Depends(get_current_user)):
 item=service.registry.get(capability_id)
 if not item: fail("CAPABILITY_NOT_FOUND")
 return CapabilitySummaryResponse(capability_id=item.id,name=item.name,description=item.description,category=item.category,version=item.version)
@router.post("/execute",response_model=CapabilityExecutionResponse)
async def execute(request:CapabilityExecutionRequest,user=Depends(get_current_user)):
 try: result,trace=service.execute(request)
 except ValueError as exc: fail(str(exc))
 return CapabilityExecutionResponse(request_id=request.request_id or trace,capability_id=request.capability_id,status=result.status,output=dict(result.metadata),warnings=list(result.warnings),trace_id=trace,framework_version="1.0",capability_version="1.0")
