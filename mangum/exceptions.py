class ASGIWebSocketCycleException(Exception):
    """Raise when an exception occurs within an ASGI websocket cycle"""


class LifespanFailure(Exception):
    """Raise when an error occurs in a lifespan event"""
