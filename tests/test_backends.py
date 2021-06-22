from unittest import mock
from typing import Any

import boto3
import pytest
import testing.redis
import testing.postgresql
from sqlalchemy import create_engine

from mangum import Mangum
from mangum.exceptions import WebSocketError, ConfigurationError
from .mock_server import s3_server, dynamodb2_server  # noqa: F401


async def dummy_coroutine(*args: Any, **kwargs: Any) -> None:
    pass


@pytest.mark.parametrize(
    "dsn", ["???://unknown/", "postgresql://", None, "http://localhost"]
)
def test_invalid_dsn(mock_ws_connect_event, mock_websocket_app, dsn):
    handler = Mangum(mock_websocket_app, dsn=dsn)
    with pytest.raises(ConfigurationError):
        handler(mock_ws_connect_event, {})


def test_sqlite_3_backend(
    tmp_path,
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
) -> None:
    dsn = f"sqlite://{tmp_path}/mangum.sqlite3"

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with mock.patch(
        "mangum.backends.WebSocket.post_to_connection", wraps=dummy_coroutine
    ), mock.patch("mangum.backends.WebSocket.delete_connection", wraps=dummy_coroutine):
        with pytest.raises(WebSocketError):
            response = handler(mock_ws_send_event, {})

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with mock.patch(
        "mangum.backends.WebSocket.post_to_connection", wraps=dummy_coroutine
    ), mock.patch("mangum.backends.WebSocket.delete_connection", wraps=dummy_coroutine):
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}


@pytest.mark.parametrize(
    "table_name",
    ["man", "mangum", "Mangum.Dev.001", "Mangum-Dev-001", "Mangum_Dev_002"],
)
def test_dynamodb_backend(
    dynamodb2_server,  # noqa: F811
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
    table_name,
) -> None:
    region_name = "ap-southeast-1"

    dsn = (
        f"dynamodb://{table_name}?region={region_name}&endpoint_url={dynamodb2_server}"
    )

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with mock.patch(
        "mangum.backends.WebSocket.post_to_connection", wraps=dummy_coroutine
    ), mock.patch("mangum.backends.WebSocket.delete_connection", wraps=dummy_coroutine):
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}

    dynamodb_resource = boto3.resource(
        "dynamodb", region_name=region_name, endpoint_url=dynamodb2_server
    )
    table = dynamodb_resource.Table(table_name)
    table.delete_item(Key={"connectionId": "d4NsecoByQ0CH-Q="})

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with pytest.raises(WebSocketError):
        response = handler(mock_ws_send_event, {})


@pytest.mark.parametrize(
    "dsn",
    [
        "s3://mangum-bucket-12345",
        "s3://mangum-bucket-12345/",
        "s3://mangum-bucket-12345/mykey/",
        "s3://mangum-bucket-12345/mykey",
    ],
)
def test_s3_backend(
    s3_server,  # noqa: F811
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
    dsn,
) -> None:
    dsn = f"{dsn}?region=ap-southeast-1&endpoint_url={s3_server}"

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with pytest.raises(WebSocketError):
        handler(mock_ws_send_event, {})

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with mock.patch(
        "mangum.backends.WebSocket.post_to_connection", wraps=dummy_coroutine
    ), mock.patch("mangum.backends.WebSocket.delete_connection", wraps=dummy_coroutine):
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}


def test_postgresql_backend(
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
):
    with testing.postgresql.Postgresql() as postgresql:
        create_engine(postgresql.url())
        dsn = postgresql.url()

        handler = Mangum(mock_websocket_app, dsn=dsn)
        with pytest.raises(WebSocketError):
            handler(mock_ws_send_event, {})

        handler = Mangum(mock_websocket_app, dsn=dsn)
        response = handler(mock_ws_connect_event, {})
        assert response == {"statusCode": 200}

        handler = Mangum(mock_websocket_app, dsn=dsn)
        with mock.patch(
            "mangum.backends.WebSocket.post_to_connection", wraps=dummy_coroutine
        ), mock.patch(
            "mangum.backends.WebSocket.delete_connection", wraps=dummy_coroutine
        ):
            response = handler(mock_ws_send_event, {})
            assert response == {"statusCode": 200}

        handler = Mangum(mock_websocket_app, dsn=dsn)
        response = handler(mock_ws_disconnect_event, {})
        assert response == {"statusCode": 200}

        handler = Mangum(mock_websocket_app, dsn=dsn)
        response = handler(mock_ws_connect_event, {})
        assert response == {"statusCode": 200}


def test_redis_backend(
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
):
    with testing.redis.RedisServer() as redis_server:
        _dsn = redis_server.dsn()
        dsn = f"redis://{_dsn['host']}:{_dsn['port']}/{_dsn['db']}"

        handler = Mangum(mock_websocket_app, dsn=dsn)
        with pytest.raises(WebSocketError):
            handler(mock_ws_send_event, {})

        handler = Mangum(mock_websocket_app, dsn=dsn)
        response = handler(mock_ws_connect_event, {})
        assert response == {"statusCode": 200}

        handler = Mangum(mock_websocket_app, dsn=dsn)
        with mock.patch(
            "mangum.backends.WebSocket.post_to_connection", wraps=dummy_coroutine
        ), mock.patch(
            "mangum.backends.WebSocket.delete_connection", wraps=dummy_coroutine
        ):
            response = handler(mock_ws_send_event, {})
            assert response == {"statusCode": 200}

        handler = Mangum(mock_websocket_app, dsn=dsn)
        response = handler(mock_ws_disconnect_event, {})
        assert response == {"statusCode": 200}
