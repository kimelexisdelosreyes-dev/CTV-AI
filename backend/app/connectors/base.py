from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.connectors.models import (
    ConnectorCapability,
    ConnectorDescriptor,
    ConnectorHealth,
    ConnectorIdentity,
    ConnectorProject,
    ConnectorSearchResult,
    ConnectorTask,
)


class ConnectorError(RuntimeError):
    pass


class ConnectorNotSupportedError(ConnectorError):
    pass


class BaseConnector(ABC):
    name: str
    display_name: str
    description: str | None = None
    enabled: bool = True
    capabilities: set[ConnectorCapability] = {
        ConnectorCapability.health,
    }

    def descriptor(self) -> ConnectorDescriptor:
        return ConnectorDescriptor(
            name=self.name,
            display_name=self.display_name,
            enabled=self.enabled,
            capabilities=sorted(self.capabilities, key=lambda item: item.value),
            description=self.description,
        )

    def supports(self, capability: ConnectorCapability) -> bool:
        return capability in self.capabilities

    @abstractmethod
    async def health(self) -> ConnectorHealth:
        raise NotImplementedError

    async def get_identity(self, user_email: str) -> ConnectorIdentity | None:
        raise ConnectorNotSupportedError(
            f"{self.name} does not support identity lookup."
        )

    async def get_tasks(
        self,
        external_user_id: str | None = None,
    ) -> Sequence[ConnectorTask]:
        raise ConnectorNotSupportedError(
            f"{self.name} does not support task retrieval."
        )

    async def get_projects(self) -> Sequence[ConnectorProject]:
        raise ConnectorNotSupportedError(
            f"{self.name} does not support project retrieval."
        )

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> Sequence[ConnectorSearchResult]:
        raise ConnectorNotSupportedError(
            f"{self.name} does not support search."
        )
