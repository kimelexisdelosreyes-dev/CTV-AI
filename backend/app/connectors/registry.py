from app.connectors.base import BaseConnector, ConnectorError


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        if connector.name in self._connectors:
            raise ConnectorError(
                f"Connector '{connector.name}' is already registered."
            )
        self._connectors[connector.name] = connector

    def replace(self, connector: BaseConnector) -> None:
        self._connectors[connector.name] = connector

    def get(self, name: str) -> BaseConnector:
        try:
            return self._connectors[name]
        except KeyError as exc:
            raise ConnectorError(
                f"Connector '{name}' is not registered."
            ) from exc

    def list(self) -> list[BaseConnector]:
        return list(self._connectors.values())

    def clear(self) -> None:
        self._connectors.clear()


connector_registry = ConnectorRegistry()
