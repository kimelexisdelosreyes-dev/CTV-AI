from app.connectors.mock import MockConnector
from app.connectors.monday import MondayConnector
from app.connectors.registry import connector_registry


def register_builtin_connectors() -> None:
    connector_registry.replace(MockConnector())
    connector_registry.replace(MondayConnector())
