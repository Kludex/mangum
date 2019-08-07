class ASGIWebSocketCycleException(Exception):
    """Raise when an exception occurs within an ASGI websocket cycle"""


class ConnectionTableException(Exception):
    """Raise when an exception occurs accessing data in the connection table"""
