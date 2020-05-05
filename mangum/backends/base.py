from dataclasses import dataclass


@dataclass
class WebSocketBackend:
    """
    Base class for implementing WebSocket backends to store API Gateway connections.

    WebSocket backends are required to implement configuration based on a `dsn`
    connection string.
    """

    dsn: str

    def create(self, connection_id: str, initial_scope: str) -> None:
        """
        Store the connection id and initial scope during the WebSocket CONNECT event.
        """
        raise NotImplementedError()

    def fetch(self, connection_id: str) -> str:
        """
        Retrieve and return the initial scope during the WebSocket MESSAGE event.
        """
        raise NotImplementedError()

    def delete(self, connection_id: str) -> None:
        """
        Delete the stored connection during the WebSocket DISCONNECT event or when
        a stale connection is detected in API Gateway.
        """
        raise NotImplementedError()
