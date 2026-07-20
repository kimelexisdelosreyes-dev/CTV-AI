from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import get_current_user
from app.db.models.user import User, UserRole
from app.schemas.operations import (
    OperationsRefreshResponse,
    OperationsSnapshotResponse,
    OperationsSyncStatusResponse,
)
from app.services.operations_snapshot_service import (
    OperationsSyncEmptyResultError,
    OperationsSyncInProgressError,
    operations_snapshot_service,
)
from app.services.service_errors import CompanyBrainServiceError


router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/snapshot", response_model=OperationsSnapshotResponse)
async def snapshot(
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
):
    result = await operations_snapshot_service.get_snapshot_response()
    result.tasks = result.tasks[offset : offset + limit]
    return result


@router.post("/refresh", response_model=OperationsRefreshResponse)
@router.post("/snapshot/refresh", response_model=OperationsRefreshResponse)
async def refresh(
    http_response: Response,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.admin, UserRole.manager}:
        raise HTTPException(status_code=403, detail="Admin or manager required.")
    try:
        snapshot = await operations_snapshot_service.sync(
            "manual", triggered_by=current_user.email
        )
        return OperationsRefreshResponse(
            status="success",
            message="Operations refresh completed.",
            running=False,
            snapshot=snapshot,
        )
    except OperationsSyncInProgressError:
        http_response.status_code = status.HTTP_202_ACCEPTED
        return OperationsRefreshResponse(
            status="running",
            message="Refresh already in progress.",
            running=True,
            snapshot=await operations_snapshot_service.get_snapshot_response(),
        )
    except OperationsSyncEmptyResultError as exc:
        return OperationsRefreshResponse(
            status="suspicious_empty",
            message=exc.safe_detail,
            running=False,
            snapshot=exc.snapshot,
        )
    except CompanyBrainServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_detail,
            headers={"X-Error-Category": exc.category},
        ) from exc


@router.get("/sync/status", response_model=OperationsSyncStatusResponse)
@router.get("/snapshot/status", response_model=OperationsSyncStatusResponse)
async def sync_status(_: User = Depends(get_current_user)):
    return await operations_snapshot_service.status()
