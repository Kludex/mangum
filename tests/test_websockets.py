import asyncio

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.websockets import WebSocket

from mangum import asgi_handler


REQUEST_EVENT = {
    "headers": {
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Host": "123456789.execute-api.ap-southeast-1.amazonaws.com",
        "Origin": "http://localhost:8000",
        "Pragma": "no-cache",
        "Sec-WebSocket-Extensions": "permessage-deflate; " "client_max_window_bits",
        "Sec-WebSocket-Key": "",
        "Sec-WebSocket-Version": "13",
        "X-Forwarded-For": "127.0.0.1",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https",
    },
    "isBase64Encoded": False,
    "multiValueHeaders": {
        "Accept-Encoding": ["gzip, deflate, br"],
        "Accept-Language": ["en-GB,en-US;q=0.9,en;q=0.8"],
        "Cache-Control": ["no-cache"],
        "Host": ["123456789.execute-api.ap-southeast-1.amazonaws.com"],
        "Origin": ["http://localhost:8000"],
        "Pragma": ["no-cache"],
        "Sec-WebSocket-Extensions": ["permessage-deflate; " "client_max_window_bits"],
        "Sec-WebSocket-Key": [""],
        "Sec-WebSocket-Version": ["13"],
        "X-Forwarded-For": ["127.0.0.1"],
        "X-Forwarded-Port": ["443"],
        "X-Forwarded-Proto": ["https"],
    },
    "requestContext": {
        "apiId": "123456789",
        "authorizer": "",
        "connectedAt": 1547717557107,
        "connectionId": "123",
        "domainName": "123456789.execute-api.ap-southeast-1.amazonaws.com",
        "error": "",
        "eventType": "CONNECT",
        "extendedRequestId": "123",
        "identity": {
            "accessKey": None,
            "accountId": None,
            "caller": None,
            "cognitoAuthenticationProvider": None,
            "cognitoAuthenticationType": None,
            "cognitoIdentityId": None,
            "cognitoIdentityPoolId": None,
            "sourceIp": "127.0.0.1",
            "user": None,
            "userAgent": None,
            "userArn": None,
        },
        "integrationLatency": "",
        "messageDirection": "IN",
        "messageId": None,
        "requestId": "123",
        "requestTime": "17/Jan/2019:09:32:37 +0000",
        "requestTimeEpoch": 1547717557114,
        "routeKey": "$connect",
        "stage": "testing",
        "status": "",
    },
}


def test_ws_response() -> None:
    class App:
        def __init__(self, scope):
            self.scope = scope

        async def __call__(self, receive, send):
            websocket = WebSocket(self.scope, receive=receive, send=send)
            await websocket.accept()
            await websocket.send_text("Hello, world!")
            await websocket.close()

    response = asgi_handler(App, REQUEST_EVENT, {})
