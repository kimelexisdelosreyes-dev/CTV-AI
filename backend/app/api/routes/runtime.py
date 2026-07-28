"""Safe, administrator-only runtime diagnostics."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.agents.bootstrap import agent_runtime_manager
from app.atlas.bootstrap import atlas_nexus_provider, atlas_runtime_manager, atlas_shadow_mode_service
from app.db.models.user import User, UserRole
from app.observability import atlas_observability_service
from app.services.inference_queue import inference_queue
from app.supervisor.service import executive_supervisor


router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/inference/status")
async def inference_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return await inference_queue.status()


@router.get("/supervisor/status")
async def supervisor_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return await executive_supervisor.status()


@router.get("/agents/status")
async def agent_runtime_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return await agent_runtime_manager.status()


@router.get("/atlas/status")
async def atlas_runtime_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    status_payload = await atlas_runtime_manager.status()
    status_payload["shadow"] = atlas_shadow_mode_service.diagnostics()
    status_payload["observability"] = atlas_observability_service.diagnostics()
    status_payload["nexus"] = atlas_nexus_provider.metrics.diagnostics()
    return status_payload
