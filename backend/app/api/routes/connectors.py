from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.connectors.base import ConnectorError
from app.connectors.manager import connector_manager
from app.connectors.models import (
    ConnectorDescriptor,
    ConnectorHealth,
    ConnectorProject,
    ConnectorSearchRequest,
    ConnectorSearchResult,
    ConnectorTask,
)
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("", response_model=list[ConnectorDescriptor])
async def list_connectors(
    _: User = Depends(get_current_user),
):
    return connector_manager.descriptors()


@router.get("/health", response_model=list[ConnectorHealth])
async def connector_health(
    _: User = Depends(get_current_user),
):
    return await connector_manager.health()


@router.get("/{connector_name}", response_model=ConnectorDescriptor)
async def get_connector(
    connector_name: str,
    _: User = Depends(get_current_user),
):
    try:
        return connector_manager.descriptor(connector_name)
    except ConnectorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{connector_name}/tasks", response_model=list[ConnectorTask])
async def connector_tasks(
    connector_name: str,
    external_user_id: str | None = None,
    _: User = Depends(get_current_user),
):
    try:
        return await connector_manager.tasks(
            connector_name,
            external_user_id,
        )
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/{connector_name}/projects",
    response_model=list[ConnectorProject],
)
async def connector_projects(
    connector_name: str,
    _: User = Depends(get_current_user),
):
    try:
        return await connector_manager.projects(connector_name)
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{connector_name}/search",
    response_model=list[ConnectorSearchResult],
)
async def connector_search(
    connector_name: str,
    request: ConnectorSearchRequest,
    _: User = Depends(get_current_user),
):
    try:
        return await connector_manager.search(
            connector_name,
            request.query,
            request.limit,
        )
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
