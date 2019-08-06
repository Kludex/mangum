# import boto3

# from mangum import Mangum

# from moto import mock_dynamodb2, mock_apigateway
# from starlette.websockets import WebSocket


# @mock_dynamodb2
# def test_websocket(mock_ws) -> None:

#     table_name = "test-table"
#     region_name = "ap-southeast-1"
#     conn = boto3.client("dynamodb", region_name=region_name)
#     conn.create_table(
#         TableName=table_name,
#         KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
#         AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
#         ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
#     )

#     async def app(scope, receive, send):
#         websocket = WebSocket(scope=scope, receive=receive, send=send)
#         await websocket.accept()
#         await websocket.send_text("Hello, world")
#         await websocket.close()

#     mock_event = mock_ws.get_connect_event()
#     handler = Mangum(app, enable_lifespan=False)
#     handler(mock_event, {})

#     mock_event = mock_ws.get_message_event()
#     handler = Mangum(app, enable_lifespan=False)
#     handler(mock_event, {})
