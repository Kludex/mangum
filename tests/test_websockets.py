import mock

from mangum import Mangum


def test_websocket_close(tmp_path, mock_ws_connect_event, mock_ws_send_event) -> None:

    dsn = f"sqlite://{tmp_path}/mangum.sqlite3"

    async def app(scope, receive, send):
        if scope["type"] == "websocket":
            while True:
                message = await receive()
                if message["type"] == "websocket.connect":
                    await send({"type": "websocket.close"})

    handler = Mangum(app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    with mock.patch("mangum.websocket.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 403}


def test_websocket_disconnect(
    tmp_path, mock_ws_connect_event, mock_ws_send_event, mock_websocket_app
) -> None:

    dsn = f"sqlite://{tmp_path}/mangum.sqlite3"

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    with mock.patch("mangum.websocket.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}


def test_websocket_exception(
    tmp_path, mock_ws_connect_event, mock_ws_send_event
) -> None:
    async def app(scope, receive, send):
        raise Exception()

    dsn = f"sqlite://{tmp_path}/mangum.sqlite3"

    handler = Mangum(app, dsn=dsn)
    handler(mock_ws_connect_event, {})

    handler = Mangum(app, dsn=dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}


def test_websocket_unexpected_message_error(
    tmp_path, mock_ws_connect_event, mock_ws_send_event
) -> None:
    async def app(scope, receive, send):
        await send({"type": "websocket.oops", "subprotocol": None})

    dsn = f"sqlite://{tmp_path}/mangum.sqlite3"

    handler = Mangum(app, dsn=dsn)
    handler(mock_ws_connect_event, {})

    handler = Mangum(app, dsn=dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}
