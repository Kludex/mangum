from dataclasses import dataclass


@dataclass
class WebSocketBackend:
    """
    Base class for implementing WebSocket backends to store API Gateway connections.

    WebSocket backends are required to implement configuration based on a `dsn`
    connection string.
    """

    dsn: str

    # async def connect(self) -> None:
    #     """
    #     """
    #     raise NotImplementedError()

    async def disconnect(self) -> None:
        """
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
