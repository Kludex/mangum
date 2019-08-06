import mock

import boto3

from mangum import Mangum

from moto import mock_dynamodb2
from starlette.websockets import WebSocket


@mock_dynamodb2
def test_websocket(mock_ws) -> None:

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
        assert scope == mock_ws.get_expected_scope()
        websocket = WebSocket(scope=scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.send_text("Hello, world")
        await websocket.close()

    mock_connect_event = mock_ws.get_connect_event()
    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_connect_event, {})
    assert response == {
        "body": "OK",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 200,
    }

    mock_send_event = mock_ws.get_send_event()
    handler = Mangum(app, enable_lifespan=False)
    with mock.patch("mangum.adapter.send_to_connections") as send_to_connections:
        send_to_connections.return_value = {"body": "OK", "status_code": 200}
        response = handler(mock_send_event, {})
