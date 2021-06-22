from dataclasses import dataclass
from typing import Any


@dataclass
class WebSocketBackend:  # pragma: no cover
    """
    Base class for implementing WebSocket backends to store API Gateway connections.

    Data source backends are required to implement configuration using the `dsn`
    connection string setting.
    """

    dsn: str

    async def __aenter__(self) -> "WebSocketBackend":
        """
        Establish the connection to a data source.
        """
        raise NotImplementedError()

    async def __aexit__(self, *exc_info: Any) -> None:
        """
        Closes the connection to a data source.
        """
        raise NotImplementedError()

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        """
        Save the JSON scope for a connection.
        """
        raise NotImplementedError()

    async def retrieve(self, connection_id: str) -> str:
        """
        Retrieve the JSON scope for a connection.
        """
        raise NotImplementedError()

    async def delete(self, connection_id: str) -> None:
        """
        Delete the JSON scope for a connection.
        """
        raise NotImplementedError()
