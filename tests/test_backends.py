import os
import mock

import pytest
import boto3
import redis
import testing.redis
import testing.postgresql
from sqlalchemy import create_engine
from moto import mock_dynamodb2, mock_s3

from mangum import Mangum
from mangum.exceptions import WebSocketError, ConfigurationError


def test_sqlite_3_backend(
    tmp_path, mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:
    valid = {
        "backend": "sqlite3",
        "params": {"file_path": os.path.join(tmp_path, "db.sqlite3")},
    }

    missing_file_path = {"backend": "sqlite3", "params": {}}

    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, ws_config=valid)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=valid)
    with mock.patch("mangum.websocket.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=valid)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}

    # Missing file path
    with pytest.raises(ConfigurationError):
        handler = Mangum(app, ws_config=missing_file_path)
        response = handler(mock_ws_connect_event, {})


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
        "params": {"table_name": table_name, "region_name": region_name},
    }
    table_does_not_exist = {
        "backend": "dynamodb",
        "params": {"table_name": "does-not-exist", "region_name": region_name},
    }
    missing_table_name = {"backend": "dynamodb", "params": {"region_name": region_name}}

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
    with mock.patch("mangum.websocket.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=valid)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}

    # Table does not exist
    handler = Mangum(app, ws_config=table_does_not_exist)
    with pytest.raises(WebSocketError):
        response = handler(mock_ws_connect_event, {})

    # Missing table name
    handler = Mangum(app, ws_config=missing_table_name)
    with pytest.raises(ConfigurationError):
        response = handler(mock_ws_connect_event, {})

    # Missing connection
    table.delete_item(Key={"connectionId": "d4NsecoByQ0CH-Q="})
    handler = Mangum(app, ws_config=valid)
    with pytest.raises(WebSocketError):
        response = handler(mock_ws_send_event, {})


@mock_s3
def test_s3_backend(
    tmp_path, mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:
    bucket = "mangum"
    conn = boto3.resource("s3")
    conn.create_bucket(Bucket=bucket)
    valid = {"backend": "s3", "params": {"bucket": bucket}}
    missing_bucket = {"backend": "s3", "params": {}}
    create_new_bucket = {"backend": "s3", "params": {"bucket": "new_bucket"}}

    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app, ws_config=valid)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=valid)
    with mock.patch("mangum.websocket.WebSocket.post_to_connection") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(app, ws_config=valid)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}

    # Missing bucket
    with pytest.raises(ConfigurationError):
        handler = Mangum(app, ws_config=missing_bucket)
        response = handler(mock_ws_connect_event, {})

    # Create bucket
    handler = Mangum(app, ws_config=create_new_bucket)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}


def test_postgresql_backend(
    mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
):
    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    with testing.postgresql.Postgresql() as postgresql:
        create_engine(postgresql.url())

        dsn = postgresql.dsn()
        params = {
            "uri": f"postgresql://{dsn['user']}:postgres@{dsn['host']}:{dsn['port']}/{dsn['database']}"
        }
        handler = Mangum(app, ws_config={"backend": "postgresql", "params": params})
        response = handler(mock_ws_connect_event, {})
        assert response == {"statusCode": 200}

        handler = Mangum(app, ws_config={"backend": "postgresql", "params": params})
        with mock.patch("mangum.websocket.WebSocket.post_to_connection") as send:
            send.return_value = None
            response = handler(mock_ws_send_event, {})
            assert response == {"statusCode": 200}

        handler = Mangum(app, ws_config={"backend": "postgresql", "params": params})
        response = handler(mock_ws_disconnect_event, {})
        assert response == {"statusCode": 200}

        dsn["password"] = "postgres"
        handler = Mangum(app, ws_config={"backend": "postgresql", "params": dsn})
        response = handler(mock_ws_connect_event, {})
        assert response == {"statusCode": 200}


def test_redis_backend(
    mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
):
    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    with testing.redis.RedisServer() as redis_server:
        dsn = redis_server.dsn()

        handler = Mangum(app, ws_config={"backend": "redis", "params": dsn})
        response = handler(mock_ws_connect_event, {})
        assert response == {"statusCode": 200}

        handler = Mangum(app, ws_config={"backend": "redis", "params": dsn})
        with mock.patch("mangum.websocket.WebSocket.post_to_connection") as send:
            send.return_value = None
            response = handler(mock_ws_send_event, {})
            assert response == {"statusCode": 200}

        handler = Mangum(app, ws_config={"backend": "redis", "params": dsn})
        response = handler(mock_ws_disconnect_event, {})
        assert response == {"statusCode": 200}
