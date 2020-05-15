import os
import pytest


@pytest.fixture
def mock_http_event(request):
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    event = {
        "path": "/test/hello",
        "body": body,
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, lzma, sdch, br",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Host": "test.execute-api.us-west-2.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-For": "192.168.100.1, 192.168.1.1",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
        },
        "pathParameters": {"proxy": "hello"},
        "requestContext": {
            "accountId": "123456789012",
            "resourceId": "us4z18",
            "stage": "Prod",
            "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
            "identity": {
                "cognitoIdentityPoolId": "",
                "accountId": "",
                "cognitoIdentityId": "",
                "caller": "",
                "apiKey": "",
                "sourceIp": "192.168.100.1",
                "cognitoAuthenticationType": "",
                "cognitoAuthenticationProvider": "",
                "userArn": "",
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
                "user": "",
            },
            "resourcePath": "/{proxy+}",
            "httpMethod": method,
            "apiId": "123",
        },
        "resource": "/{proxy+}",
        "httpMethod": method,
        "queryStringParameters": {
            k: v[0] for k, v in multi_value_query_parameters.items()
        }
        if multi_value_query_parameters
        else None,
        "multiValueQueryStringParameters": multi_value_query_parameters or None,
        "stageVariables": {"stageVarName": "stageVarValue"},
    }
    return event


@pytest.fixture
def mock_http_api_event(request):
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    query_string = request.param[3]
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/my/path",
        "rawQueryString": query_string,
        "cookies": ["cookie1", "cookie2"],
        "headers": {
            "accept-encoding": "gzip,deflate",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
            "host": "test.execute-api.us-west-2.amazonaws.com",
        },
        "queryStringParameters": {
            k: v[0] for k, v in multi_value_query_parameters.items()
        }
        if multi_value_query_parameters
        else None,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "authorizer": {
                "jwt": {
                    "claims": {"claim1": "value1", "claim2": "value2"},
                    "scopes": ["scope1", "scope2"],
                }
            },
            "domainName": "id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "id",
            "http": {
                "method": method,
                "path": "/my/path",
                "protocol": "HTTP/1.1",
                "sourceIp": "192.168.100.1",
                "userAgent": "agent",
            },
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390,
        },
        "body": body,
        "pathParameters": {"parameter1": "value1"},
        "isBase64Encoded": False,
        "stageVariables": {"stageVariable1": "value1", "stageVariable2": "value2"},
    }

    return event


@pytest.fixture
def mock_ws_connect_event() -> dict:
    return {
        "headers": {
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Host": "test.execute-api.ap-southeast-1.amazonaws.com",
            "Origin": "https://test.execute-api.ap-southeast-1.amazonaws.com",
            "Pragma": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; " "client_max_window_bits",
            "Sec-WebSocket-Key": "bnfeqmh9SSPr5Sg9DvFIBw==",
            "Sec-WebSocket-Version": "13",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/75.0.3770.100 Safari/537.36",
            "X-Amzn-Trace-Id": "Root=1-5d465cb6-78ddcac1e21f89203d004a89",
            "X-Forwarded-For": "192.168.100.1",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
        },
        "isBase64Encoded": False,
        "multiValueHeaders": {
            "Accept-Encoding": ["gzip, deflate, br"],
            "Accept-Language": ["en-US,en;q=0.9"],
            "Cache-Control": ["no-cache"],
            "Host": ["test.execute-api.ap-southeast-1.amazonaws.com"],
            "Origin": ["https://test.execute-api.ap-southeast-1.amazonaws.com"],
            "Pragma": ["no-cache"],
            "Sec-WebSocket-Extensions": [
                "permessage-deflate; " "client_max_window_bits"
            ],
            "Sec-WebSocket-Key": ["bnfeqmh9SSPr5Sg9DvFIBw=="],
            "Sec-WebSocket-Version": ["13"],
            "User-Agent": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X "
                "10_14_5) AppleWebKit/537.36 (KHTML, "
                "like Gecko) Chrome/75.0.3770.100 "
                "Safari/537.36"
            ],
            "X-Amzn-Trace-Id": ["Root=1-5d465cb6-78ddcac1e21f89203d004a89"],
            "X-Forwarded-For": ["192.168.100.1"],
            "X-Forwarded-Port": ["443"],
            "X-Forwarded-Proto": ["https"],
        },
        "requestContext": {
            "apiId": "test",
            "connectedAt": 1564892342293,
            "connectionId": "d4NsecoByQ0CH-Q=",
            "domainName": "test.execute-api.ap-southeast-1.amazonaws.com",
            "eventType": "CONNECT",
            "extendedRequestId": "d4NseGc4yQ0FsSA=",
            "identity": {
                "accessKey": None,
                "accountId": None,
                "caller": None,
                "cognitoAuthenticationProvider": None,
                "cognitoAuthenticationType": None,
                "cognitoIdentityId": None,
                "cognitoIdentityPoolId": None,
                "principalOrgId": None,
                "sourceIp": "192.168.100.1",
                "user": None,
                "userAgent": "Mozilla/5.0 (Macintosh; Intel "
                "Mac OS X 10_14_5) "
                "AppleWebKit/537.36 (KHTML, like "
                "Gecko) Chrome/75.0.3770.100 "
                "Safari/537.36",
                "userArn": None,
            },
            "messageDirection": "IN",
            "messageId": None,
            "requestId": "d4NseGc4yQ0FsSA=",
            "requestTime": "04/Aug/2019:04:19:02 +0000",
            "requestTimeEpoch": 1564892342293,
            "routeKey": "$connect",
            "stage": "Prod",
        },
    }


@pytest.fixture
def mock_ws_send_event() -> dict:
    return {
        "body": '{"action": "sendmessage", "data": "Hello world"}',
        "isBase64Encoded": False,
        "requestContext": {
            "apiId": "test",
            "connectedAt": 1564984321285,
            "connectionId": "d4NsecoByQ0CH-Q=",
            "domainName": "test.execute-api.ap-southeast-1.amazonaws.com",
            "eventType": "MESSAGE",
            "extendedRequestId": "d7uRtFvnyQ0FYmw=",
            "identity": {
                "accessKey": None,
                "accountId": None,
                "caller": None,
                "cognitoAuthenticationProvider": None,
                "cognitoAuthenticationType": None,
                "cognitoIdentityId": None,
                "cognitoIdentityPoolId": None,
                "principalOrgId": None,
                "sourceIp": "192.168.100.1",
                "user": None,
                "userAgent": None,
                "userArn": None,
            },
            "messageDirection": "IN",
            "messageId": "d7uRtfaKSQ0CE4Q=",
            "requestId": "d7uRtFvnyQ0FYmw=",
            "requestTime": "05/Aug/2019:05:52:10 +0000",
            "requestTimeEpoch": 1564984330952,
            "routeKey": "sendmessage",
            "stage": "Prod",
        },
    }


@pytest.fixture
def mock_ws_disconnect_event() -> dict:
    return {
        "headers": {
            "Host": "test.execute-api.ap-southeast-1.amazonaws.com",
            "x-api-key": "",
            "x-restapi": "",
        },
        "isBase64Encoded": False,
        "multiValueHeaders": {
            "Host": ["test.execute-api.ap-southeast-1.amazonaws.com"],
            "x-api-key": [""],
            "x-restapi": [""],
        },
        "requestContext": {
            "apiId": "test",
            "connectedAt": 1565140098258,
            "connectionId": "d4NsecoByQ0CH-Q=",
            "domainName": "test.execute-api.ap-southeast-1.amazonaws.com",
            "eventType": "DISCONNECT",
            "extendedRequestId": "eBql1FJmSQ0FrjA=",
            "identity": {
                "accessKey": None,
                "accountId": None,
                "caller": None,
                "cognitoAuthenticationProvider": None,
                "cognitoAuthenticationType": None,
                "cognitoIdentityId": None,
                "cognitoIdentityPoolId": None,
                "principalOrgId": None,
                "sourceIp": "101.164.35.219",
                "user": None,
                "userAgent": "Mozilla/5.0 (Macintosh; Intel "
                "Mac OS X 10_14_6) "
                "AppleWebKit/537.36 (KHTML, like "
                "Gecko) Chrome/75.0.3770.142 "
                "Safari/537.36",
                "userArn": None,
            },
            "messageDirection": "IN",
            "messageId": None,
            "requestId": "eBql1FJmSQ0FrjA=",
            "requestTime": "07/Aug/2019:01:08:27 +0000",
            "requestTimeEpoch": 1565140107779,
            "routeKey": "$disconnect",
            "stage": "Prod",
        },
    }


@pytest.fixture
def mock_websocket_app():
    async def app(scope, receive, send):
        if scope["type"] == "websocket":
            while True:
                message = await receive()
                if message["type"] == "websocket.connect":
                    await send({"type": "websocket.accept", "subprotocol": None})
                elif message["type"] == "websocket.receive":
                    await send({"type": "websocket.send", "text": "Hello world!"})
                elif message["type"] == "websocket.disconnect":
                    close_code = message.get("code", 1000)
                    await send({"type": "websocket.close", "code": close_code})
                    return

    return app


def pytest_generate_tests(metafunc):
    os.environ["AWS_REGION"] = "ap-southeast-1"
