import mock

import os
import boto3
from moto import mock_dynamodb2
from starlette.applications import Starlette

from mangum import Mangum


def create_dynamo_db_table(table_name: str = "mangum"):
    dynamodb_resource = boto3.resource("dynamodb", region_name="ap-southeast-1")
    dynamodb_resource.meta.client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    dynamodb_table = dynamodb_resource.Table(table_name)

    return dynamodb_table


@mock_dynamodb2
def test_websocket_events(
    mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
) -> None:
    create_dynamo_db_table()

    async def app(scope, receive, send):
        await send({"type": "websocket.accept", "subprotocol": None})
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.send", "bytes": b"Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(app)
    with mock.patch("mangum.connections.WebSocket.send") as send:
        send.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}

    handler = Mangum(app)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}


@mock_dynamodb2
def test_websocket_cycle_state(mock_ws_connect_event, mock_ws_send_event) -> None:
    create_dynamo_db_table()

    async def app(scope, receive, send):
        await send({"type": "websocket.send", "text": "Hello world!"})

    handler = Mangum(app)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}
    handler = Mangum(app)
    with mock.patch("mangum.connections.WebSocket.send") as send_data:
        send_data.return_value = None
        handler(mock_ws_send_event, {})


@mock_dynamodb2
def test_websocket_table_does_not_exist(mock_ws_connect_event) -> None:
    create_dynamo_db_table(table_name="not-mangum")

    async def app(scope, receive, send):
        await send({"type": "websocket.send", "text": "Hello world!"})

    handler = Mangum(app)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 500}


@mock_dynamodb2
def test_websocket_client_already_exists(mock_ws_connect_event) -> None:
    table = create_dynamo_db_table()
    table.put_item(Item={"connectionId": "d4NsecoByQ0CH-Q="})

    async def app(scope, receive, send):
        await send({"type": "websocket.send", "text": "Hello world!"})

    handler = Mangum(app)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 500}


@mock_dynamodb2
def test_websocket_client_does_not_exist(
    mock_ws_send_event, mock_ws_disconnect_event
) -> None:
    table = create_dynamo_db_table()
    table.delete_item(Key={"connectionId": "d4NsecoByQ0CH-Q="})

    async def app(scope, receive, send):
        await send({"type": "websocket.send", "text": "Hello world!"})
        await send({"type": "websocket.close", "code": 1000})

    handler = Mangum(app)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}


@mock_dynamodb2
def test_websocket_cycle_exception(mock_ws_connect_event, mock_ws_send_event) -> None:
    create_dynamo_db_table()

    async def app(scope, receive, send):
        await send({"type": "websocket.oops", "subprotocol": None})

    handler = Mangum(app)
    handler(mock_ws_connect_event, {})

    handler = Mangum(app)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 500}


def test_websocket_env_vars(mock_ws_connect_event) -> None:
    async def app(scope, receive, send):
        await send({"type": "websocket.send", "text": "Hello world!"})

    os.environ.pop("TABLE_NAME")
    handler = Mangum(app)
    handler(mock_ws_connect_event, {})
    os.environ["TABLE_NAME"] = "mangum"


@mock_dynamodb2
def test_starlette_websocket(mock_ws_connect_event, mock_ws_send_event) -> None:
    create_dynamo_db_table()
    app = Starlette()

    @app.websocket_route("/ws")
    async def websocket_endpoint(websocket):
        await websocket.accept()
        await websocket.send_json({"url": str(websocket.url)})
        await websocket.close()

    handler = Mangum(app)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    handler = Mangum(app)
    with mock.patch("mangum.connections.WebSocket.send") as send_data:
        send_data.return_value = None
        response = handler(mock_ws_send_event, {})
        assert response == {"statusCode": 200}
