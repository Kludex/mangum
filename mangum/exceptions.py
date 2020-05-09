class LifespanFailure(Exception):
    """Raise when an error occurs in a lifespan event"""


class WebSocketError(Exception):
    """Raise when an error occurs in a WebSocket event."""


class ConfigurationError(Exception):
    """Raise when an error occurs parsing configuration."""
