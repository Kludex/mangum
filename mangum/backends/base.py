from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator


@dataclass
class WebSocketBackend:
    """
    Base class for implementing WebSocket backends to store API Gateway connections.

    Data source backends are required to implement configuration using the `dsn`
    connection string setting.
    """

    dsn: str

    @asynccontextmanager  # type: ignore
    async def connect(self) -> AsyncIterator:
        """
        Establish the connection to a data source.
        """
        raise NotImplementedError()  # pragma: no cover

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        """
        Save the JSON scope for a connection.
        """
        raise NotImplementedError()  # pragma: no cover

    async def retrieve(self, connection_id: str) -> str:
        """
        Retrieve the JSON scope for a connection.
        """
        raise NotImplementedError()  # pragma: no cover

    async def delete(self, connection_id: str) -> None:
        """
        Delete the JSON scope for a connection.
        """
        raise NotImplementedError()  # pragma: no cover
