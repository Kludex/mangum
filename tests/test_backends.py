import os
import mock

import pytest
import boto3
from moto import mock_dynamodb2, mock_s3

from mangum import Mangum
from mangum.exceptions import WebSocketError


def test_sqlite_3_backend(
    tmp_path, mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:
    ws_config = {
        "backend": "sqlite3",
        "file_path": os.path.join(tmp_path, "db.sqlite3"),
    }

    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, ws_config=ws_config)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=ws_config)
    with mock.patch("mangum.websockets.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=ws_config)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}


@mock_dynamodb2
def test_dynamodb_backend(
    mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:
    table_name = "mangum"
    region_name = "ap-southeast-1"
    dynamodb_resource = boto3.resource("dynamodb", region_name=region_name)
    dynamodb_resource.meta.client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb_resource.Table(table_name)

    valid = {
        "backend": "dynamodb",
        "table_name": table_name,
        "region_name": region_name,
    }
    table_does_not_exist = {
        "backend": "dynamodb",
        "table_name": "does-not-exist",
        "region_name": region_name,
    }

    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    # Test valid cases
    handler = Mangum(app, ws_config=valid)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=valid)
    with mock.patch("mangum.websockets.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=valid)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}

    # Test table does not exist
    handler = Mangum(app, ws_config=table_does_not_exist)
    with pytest.raises(WebSocketError):
        response = handler(mock_ws_connect_event, {})

    # Test missing connection
    table.delete_item(Key={"connectionId": "d4NsecoByQ0CH-Q="})
    handler = Mangum(app, ws_config=valid)
    with pytest.raises(WebSocketError):
        response = handler(mock_ws_send_event, {})


@mock_s3
def test_s3_backend(
    tmp_path, mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:
    bucket_name = "mangum"
    conn = boto3.resource("s3")
    conn.create_bucket(Bucket=bucket_name)

    ws_config = {"backend": "s3", "bucket_name": bucket_name}

    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, ws_config=ws_config)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=ws_config)
    with mock.patch("mangum.websockets.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=ws_config)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}
