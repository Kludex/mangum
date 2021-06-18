from dataclasses import dataclass
from typing import AsyncIterator

from .._compat import asynccontextmanager


@dataclass
class WebSocketBackend:
    """
    Base class for implementing WebSocket backends to store API Gateway connections.

    Data source backends are required to implement configuration using the `dsn`
    connection string setting.
    """

    dsn: str

    @asynccontextmanager  # type: ignore
    async def connect(self) -> AsyncIterator:  # pragma: no cover
        """
        Establish the connection to a data source.
        """
        yield
        raise NotImplementedError()

    async def save(
        self, connection_id: str, *, json_scope: str
    ) -> None:  # pragma: no cover
        """
        Save the JSON scope for a connection.
        """
        raise NotImplementedError()

    async def retrieve(self, connection_id: str) -> str:  # pragma: no cover
        """
        Retrieve the JSON scope for a connection.
        """
        raise NotImplementedError()

    async def delete(self, connection_id: str) -> None:  # pragma: no cover
        """
        Delete the JSON scope for a connection.
        """
        raise NotImplementedError()
