import pytest

import os

from starlette.applications import Starlette

from mangum import Mangum
from mangum.exceptions import WebSocketError


def test_ws_config_missing(mock_ws_connect_event):
    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, ws_config=None)
    with pytest.raises(WebSocketError):
        handler(mock_ws_connect_event, {})


def test_ws_config_unknown_backend(mock_ws_connect_event):
    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, ws_config={"backend": "unknown"})
    with pytest.raises(WebSocketError):
        handler(mock_ws_connect_event, {})


def test_websocket_cycle_exception(
    tmp_path, mock_ws_connect_event, mock_ws_send_event
) -> None:
    async def app(scope, receive, send):
        await send({"type": "websocket.oops", "subprotocol": None})

    ws_config = {
        "backend": "sqlite3",
        "file_path": os.path.join(tmp_path, "db.sqlite3"),
    }

    handler = Mangum(app, ws_config=ws_config)
    handler(mock_ws_connect_event, {})

    handler = Mangum(app, ws_config=ws_config)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}
