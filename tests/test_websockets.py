from unittest import mock
from typing import Any

import respx

from mangum import Mangum


async def dummy_coroutine(*args: Any, **kwargs: Any) -> None:
    pass


@respx.mock(assert_all_mocked=False)
def test_websocket_close(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event
) -> None:
    async def app(scope, receive, send):
        if scope["type"] == "websocket":
            while True:
                message = await receive()
                if message["type"] == "websocket.connect":
                    await send({"type": "websocket.close"})

    handler = Mangum(app, lifespan="off", dsn=sqlite3_dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 403}


@respx.mock(assert_all_mocked=False)
def test_websocket_disconnect(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event, mock_websocket_app
) -> None:
    handler = Mangum(mock_websocket_app, lifespan="off", dsn=sqlite3_dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 200}


def test_websocket_exception(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event
) -> None:
    async def app(scope, receive, send):
        raise Exception()

    handler = Mangum(app, dsn=sqlite3_dsn)
    handler(mock_ws_connect_event, {})

    handler = Mangum(app, dsn=sqlite3_dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}


def test_websocket_unexpected_message_error(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event
) -> None:
    async def app(scope, receive, send):
        await send({"type": "websocket.oops", "subprotocol": None})

    handler = Mangum(app, dsn=sqlite3_dsn)
    handler(mock_ws_connect_event, {})

    handler = Mangum(app, dsn=sqlite3_dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}


@respx.mock(assert_all_mocked=False)
def test_websocket_without_body(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event, mock_websocket_app
) -> None:
    handler = Mangum(mock_websocket_app, lifespan="off", dsn=sqlite3_dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    del mock_ws_send_event["body"]
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 200}


def test_base64_encoded_body_on_request(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event, mock_websocket_app
):
    handler = Mangum(mock_websocket_app, dsn=sqlite3_dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    mock_ws_send_event["body"] = b"bWFuZ3Vt="
    mock_ws_send_event["isBase64Encoded"] = True
    with mock.patch(
        "mangum.backends.WebSocket.post_to_connection", wraps=dummy_coroutine
    ), mock.patch("mangum.backends.WebSocket.delete_connection", wraps=dummy_coroutine):
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}


def test_binary_response(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event, mock_websocket_app
):
    async def app(scope, receive, send):
        if scope["type"] == "websocket":
            while True:
                message = await receive()
                if message["type"] == "websocket.connect":
                    await send({"type": "websocket.accept"})
                elif message["type"] == "websocket.receive":
                    await send({"type": "websocket.send", "body": b"bWFuZ3Vt="})

    handler = Mangum(app, dsn=sqlite3_dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}
