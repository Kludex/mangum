import mock
import pytest
import boto3
from moto import mock_dynamodb2
from mangum import Mangum


@mock_dynamodb2
def test_websocket_events(
    mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:

    table_name = "test-table"
    region_name = "ap-southeast-1"
    conn = boto3.client("dynamodb", region_name=region_name)
    conn.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    async def app(scope, receive, send):
        assert scope == {
            "client": ["192.168.100.1", 0],
            "headers": [
                [b"Accept-Encoding", b"gzip, deflate, br"],
                [b"Accept-Language", b"en-US,en;q=0.9"],
                [b"Cache-Control", b"no-cache"],
                [b"Host", b"test.execute-api.ap-southeast-1.amazonaws.com"],
                [b"Origin", b"https://test.execute-api.ap-southeast-1.amazonaws.com"],
                [b"Pragma", b"no-cache"],
                [
                    b"Sec-WebSocket-Extensions",
                    b"permessage-deflate; client_max_window_bits",
                ],
                [b"Sec-WebSocket-Key", b"bnfeqmh9SSPr5Sg9DvFIBw=="],
                [b"Sec-WebSocket-Version", b"13"],
                [
                    b"User-Agent",
                    b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/"
                    b"537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
                ],
                [b"X-Amzn-Trace-Id", b"Root=1-5d465cb6-78ddcac1e21f89203d004a89"],
                [b"X-Forwarded-For", b"192.168.100.1"],
                [b"X-Forwarded-Port", b"443"],
                [b"X-Forwarded-Proto", b"https"],
            ],
            "path": "/ws",
            "query_string": b"",
            "raw_path": None,
            "root_path": "Prod",
            "scheme": "https",
            "server": ["test.execute-api.ap-southeast-1.amazonaws.com", 80],
            "type": "websocket",
        }

        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_ws_connect_event, {})
    assert response == {
        "body": "OK",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 200,
    }

    handler = Mangum(app, enable_lifespan=False)
    with mock.patch("mangum.asgi.ASGIWebSocketCycle.send_data") as send_data:
        send_data.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {
            "body": "OK",
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "isBase64Encoded": False,
            "statusCode": 200,
        }

    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {
        "body": "OK",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 200,
    }


@mock_dynamodb2
def test_websocket_cycle_state(mock_ws_connect_event, mock_ws_send_event) -> None:

    table_name = "test-table"
    region_name = "ap-southeast-1"
    conn = boto3.client("dynamodb", region_name=region_name)
    conn.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    async def app(scope, receive, send):
        await send({"type": "websocket.send", "text": "Hello world!"})

    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_ws_connect_event, {})
    assert response == {
        "body": "OK",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 200,
    }

    handler = Mangum(app, enable_lifespan=False)

    with pytest.raises(RuntimeError):
        with mock.patch("mangum.asgi.ASGIWebSocketCycle.send_data") as send_data:
            send_data.return_value = None
            handler(mock_ws_send_event, {})


@mock_dynamodb2
def test_websocket_group_events(
    mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:

    table_name = "test-table"
    region_name = "ap-southeast-1"
    conn = boto3.client("dynamodb", region_name=region_name)
    conn.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    async def app(scope, receive, send):
        assert scope == {
            "client": ["192.168.100.1", 0],
            "headers": [
                [b"Accept-Encoding", b"gzip, deflate, br"],
                [b"Accept-Language", b"en-US,en;q=0.9"],
                [b"Cache-Control", b"no-cache"],
                [b"Host", b"test.execute-api.ap-southeast-1.amazonaws.com"],
                [b"Origin", b"https://test.execute-api.ap-southeast-1.amazonaws.com"],
                [b"Pragma", b"no-cache"],
                [
                    b"Sec-WebSocket-Extensions",
                    b"permessage-deflate; client_max_window_bits",
                ],
                [b"Sec-WebSocket-Key", b"bnfeqmh9SSPr5Sg9DvFIBw=="],
                [b"Sec-WebSocket-Version", b"13"],
                [
                    b"User-Agent",
                    b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/"
                    b"537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
                ],
                [b"X-Amzn-Trace-Id", b"Root=1-5d465cb6-78ddcac1e21f89203d004a89"],
                [b"X-Forwarded-For", b"192.168.100.1"],
                [b"X-Forwarded-Port", b"443"],
                [b"X-Forwarded-Proto", b"https"],
            ],
            "path": "/ws",
            "query_string": b"",
            "raw_path": None,
            "root_path": "Prod",
            "scheme": "https",
            "server": ["test.execute-api.ap-southeast-1.amazonaws.com", 80],
            "type": "websocket",
        }

        await send({"type": "websocket.accept", "subprotocol": None})
        await send(
            {"type": "websocket.send", "text": "Hello world!", "group": "testgroup"}
        )
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_ws_connect_event, {})
    assert response == {
        "body": "OK",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 200,
    }

    handler = Mangum(app, enable_lifespan=False)
    with mock.patch("mangum.asgi.ASGIWebSocketCycle.send_data") as send_data:
        send_data.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {
            "body": "OK",
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "isBase64Encoded": False,
            "statusCode": 200,
        }

    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {
        "body": "OK",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 200,
    }
