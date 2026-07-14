import asyncio

from app.connectors.base import ConnectorError, ConnectorNotSupportedError
from app.connectors.models import (
    ConnectorCapability,
    ConnectorDescriptor,
    ConnectorHealth,
    ConnectorProject,
    ConnectorSearchResult,
    ConnectorTask,
)
from app.connectors.registry import connector_registry


class ConnectorManager:
    def descriptors(self) -> list[ConnectorDescriptor]:
        return [
            connector.descriptor()
            for connector in connector_registry.list()
        ]

    def descriptor(self, name: str) -> ConnectorDescriptor:
        return connector_registry.get(name).descriptor()

    async def health(self) -> list[ConnectorHealth]:
        connectors = connector_registry.list()

        if not connectors:
            return []

        results = await asyncio.gather(
            *(connector.health() for connector in connectors),
            return_exceptions=True,
        )

        health_items: list[ConnectorHealth] = []

        for connector, result in zip(connectors, results, strict=True):
            if isinstance(result, Exception):
                from datetime import datetime, timezone
                from app.connectors.models import ConnectorStatus

                health_items.append(
                    ConnectorHealth(
                        name=connector.name,
                        status=ConnectorStatus.unavailable,
                        checked_at=datetime.now(timezone.utc),
                        detail=str(result),
                    )
                )
            else:
                health_items.append(result)

        return health_items

    async def tasks(
        self,
        name: str,
        external_user_id: str | None = None,
    ) -> list[ConnectorTask]:
        connector = connector_registry.get(name)

        if not connector.supports(ConnectorCapability.tasks):
            raise ConnectorNotSupportedError(
                f"Connector '{name}' does not support tasks."
            )

        return list(await connector.get_tasks(external_user_id))

    async def projects(self, name: str) -> list[ConnectorProject]:
        connector = connector_registry.get(name)

        if not connector.supports(ConnectorCapability.projects):
            raise ConnectorNotSupportedError(
                f"Connector '{name}' does not support projects."
            )

        return list(await connector.get_projects())

    async def search(
        self,
        name: str,
        query: str,
        limit: int,
    ) -> list[ConnectorSearchResult]:
        connector = connector_registry.get(name)

        if not connector.supports(ConnectorCapability.search):
            raise ConnectorNotSupportedError(
                f"Connector '{name}' does not support search."
            )

        return list(await connector.search(query, limit))


connector_manager = ConnectorManager()
