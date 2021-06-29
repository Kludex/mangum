import pytest
import boto3
import respx

from mangum import Mangum
from mangum.exceptions import WebSocketError, ConfigurationError
from .mock_server import (
    start_service,
    stop_process,
    wait_postgres_server,
    wait_redis_server,
)

pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="session")
def dynamodb2_server():
    host = "localhost"
    port = 5001
    url = f"http://{host}:{port}"
    process = start_service("dynamodb2", host, port)
    yield url
    stop_process(process)


@pytest.fixture(scope="session")
def s3_server():
    host = "localhost"
    port = 5002
    url = f"http://{host}:{port}"
    process = start_service("s3", host, port)
    yield url
    stop_process(process)


@pytest.fixture(scope="module")
def postgres_server(module_scoped_container_getter):
    container = module_scoped_container_getter.get("postgres")
    network = container.network_info[0]
    hostname = network.hostname
    host_port = network.host_port
    dsn = f"postgresql://postgres:mangum@{hostname}:{host_port}/postgres"
    wait_postgres_server(dsn)

    try:
        yield dsn
    finally:
        container.stop()


@pytest.fixture(scope="module")
def redis_server(module_scoped_container_getter):
    container = module_scoped_container_getter.get("redis")
    network = container.network_info[0]
    hostname = network.hostname
    host_port = int(network.host_port)
    dsn = f"redis://{hostname}:{host_port}"
    wait_redis_server(hostname, host_port)

    try:
        yield dsn
    finally:
        container.stop()


@pytest.mark.parametrize(
    "dsn", ["???://unknown/", "postgresql://", None, "http://localhost"]
)
def test_invalid_dsn(mock_ws_connect_event, mock_websocket_app, dsn):
    handler = Mangum(mock_websocket_app, dsn=dsn)
    with pytest.raises(ConfigurationError):
        handler(mock_ws_connect_event, {})


@respx.mock(assert_all_mocked=False)
def test_sqlite_3_backend(
    tmp_path,
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
) -> None:
    dsn = f"sqlite://{tmp_path}/mangum.sqlite3"

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with pytest.raises(WebSocketError):
        response = handler(mock_ws_send_event, {})

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}


@respx.mock(assert_all_mocked=False)
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


@respx.mock(assert_all_mocked=False)
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
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}


@respx.mock(assert_all_mocked=False)
def test_postgresql_backend(
    postgres_server,
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
):
    dsn = postgres_server

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with pytest.raises(WebSocketError):
        handler(mock_ws_send_event, {})

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}


@respx.mock(assert_all_mocked=False)
def test_redis_backend(
    redis_server,
    mock_ws_connect_event,
    mock_ws_send_event,
    mock_ws_disconnect_event,
    mock_websocket_app,
):
    dsn = redis_server

    handler = Mangum(mock_websocket_app, dsn=dsn)
    with pytest.raises(WebSocketError):
        handler(mock_ws_send_event, {})

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(mock_websocket_app, dsn=dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}
