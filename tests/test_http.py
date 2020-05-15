import base64
import urllib.parse
import json
import gzip

import pytest
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import PlainTextResponse
from mangum import Mangum


@pytest.mark.parametrize(
    "mock_http_event,query_string",
    [
        (["GET", None, None], b""),
        (["GET", None, {"name": ["me"]}], b"name=me"),
        (["GET", None, {"name": ["me", "you"]}], b"name=me&name=you"),
        (
            ["GET", None, {"name": ["me", "you"], "pet": ["dog"]}],
            b"name=me&name=you&pet=dog",
        ),
    ],
    indirect=["mock_http_event"],
)
def test_http_request(mock_http_event, query_string) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "body": None,
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, lzma, sdch, " "br",
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
                "httpMethod": "GET",
                "path": "/test/hello",
                "pathParameters": {"proxy": "hello"},
                "queryStringParameters": mock_http_event["queryStringParameters"],
                "multiValueQueryStringParameters": mock_http_event[
                    "multiValueQueryStringParameters"
                ],
                "requestContext": {
                    "accountId": "123456789012",
                    "apiId": "123",
                    "httpMethod": "GET",
                    "identity": {
                        "accountId": "",
                        "apiKey": "",
                        "caller": "",
                        "cognitoAuthenticationProvider": "",
                        "cognitoAuthenticationType": "",
                        "cognitoIdentityId": "",
                        "cognitoIdentityPoolId": "",
                        "sourceIp": "192.168.100.1",
                        "user": "",
                        "userAgent": "Mozilla/5.0 "
                        "(Macintosh; "
                        "Intel Mac OS "
                        "X 10_11_6) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like "
                        "Gecko) "
                        "Chrome/52.0.2743.82 "
                        "Safari/537.36 "
                        "OPR/39.0.2256.48",
                        "userArn": "",
                    },
                    "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
                    "resourceId": "us4z18",
                    "resourcePath": "/{proxy+}",
                    "stage": "Prod",
                },
                "resource": "/{proxy+}",
                "stageVariables": {"stageVarName": "stageVarValue"},
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [
                    b"accept",
                    b"text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                    b"webp,*/*;q=0.8",
                ],
                [b"accept-encoding", b"gzip, deflate, lzma, sdch, br"],
                [b"accept-language", b"en-US,en;q=0.8"],
                [b"cloudfront-forwarded-proto", b"https"],
                [b"cloudfront-is-desktop-viewer", b"true"],
                [b"cloudfront-is-mobile-viewer", b"false"],
                [b"cloudfront-is-smarttv-viewer", b"false"],
                [b"cloudfront-is-tablet-viewer", b"false"],
                [b"cloudfront-viewer-country", b"US"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"upgrade-insecure-requests", b"1"],
                [b"x-forwarded-for", b"192.168.100.1, 192.168.1.1"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/test/hello",
            "query_string": query_string,
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 80),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_http_event", [["GET", None, {"name": ["me", "you"]}]], indirect=True
)
def test_http_response(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "body": None,
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, lzma, sdch, " "br",
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
                "httpMethod": "GET",
                "path": "/test/hello",
                "pathParameters": {"proxy": "hello"},
                "queryStringParameters": {"name": "me"},
                "multiValueQueryStringParameters": {"name": ["me", "you"]},
                "requestContext": {
                    "accountId": "123456789012",
                    "apiId": "123",
                    "httpMethod": "GET",
                    "identity": {
                        "accountId": "",
                        "apiKey": "",
                        "caller": "",
                        "cognitoAuthenticationProvider": "",
                        "cognitoAuthenticationType": "",
                        "cognitoIdentityId": "",
                        "cognitoIdentityPoolId": "",
                        "sourceIp": "192.168.100.1",
                        "user": "",
                        "userAgent": "Mozilla/5.0 "
                        "(Macintosh; "
                        "Intel Mac OS "
                        "X 10_11_6) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like "
                        "Gecko) "
                        "Chrome/52.0.2743.82 "
                        "Safari/537.36 "
                        "OPR/39.0.2256.48",
                        "userArn": "",
                    },
                    "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
                    "resourceId": "us4z18",
                    "resourcePath": "/{proxy+}",
                    "stage": "Prod",
                },
                "resource": "/{proxy+}",
                "stageVariables": {"stageVarName": "stageVarValue"},
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [
                    b"accept",
                    b"text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                    b"webp,*/*;q=0.8",
                ],
                [b"accept-encoding", b"gzip, deflate, lzma, sdch, br"],
                [b"accept-language", b"en-US,en;q=0.8"],
                [b"cloudfront-forwarded-proto", b"https"],
                [b"cloudfront-is-desktop-viewer", b"true"],
                [b"cloudfront-is-mobile-viewer", b"false"],
                [b"cloudfront-is-smarttv-viewer", b"false"],
                [b"cloudfront-is-tablet-viewer", b"false"],
                [b"cloudfront-viewer-country", b"US"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"upgrade-insecure-requests", b"1"],
                [b"x-forwarded-for", b"192.168.100.1, 192.168.1.1"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/test/hello",
            "query_string": b"name=me&name=you",
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "123", None]], indirect=True)
def test_http_response_with_body(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"

        body = [b"4", b"5", b"6"]

        while True:
            message = await receive()
            if "body" in message:
                body.append(message["body"])

            if not message.get("more_body", False):
                body = b"".join(body)
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "456123",
    }


@pytest.mark.parametrize(
    "mock_http_event", [["GET", base64.b64encode(b"123"), None]], indirect=True
)
def test_http_binary_request_with_body(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"

        body = []
        message = await receive()

        if "body" in message:
            body.append(message["body"])

        if not message.get("more_body", False):

            body = b"".join(body)
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": body})

    mock_http_event["isBase64Encoded"] = True
    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "123",
    }


@pytest.mark.parametrize(
    "mock_http_event", [["GET", base64.b64encode(b"123"), None]], indirect=True
)
def test_http_binary_request_and_response(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"

        body = []
        message = await receive()

        if "body" in message:
            body.append(message["body"])

        if not message.get("more_body", False):

            body = b"".join(body)
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/octet-stream"]],
                }
            )
            await send({"type": "http.response.body", "body": b"abc"})

    mock_http_event["isBase64Encoded"] = True
    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {"content-type": "application/octet-stream"},
        "body": base64.b64encode(b"abc").decode(),
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_http_exception(mock_http_event) -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200})
        raise Exception()
        await send({"type": "http.response.body", "body": b"1", "more_body": True})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "body": "Internal Server Error",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_http_exception_handler(mock_http_event) -> None:
    path = mock_http_event["path"]
    app = Starlette()

    @app.exception_handler(Exception)
    async def all_exceptions(request, exc):
        return PlainTextResponse(content="Error!", status_code=500)

    @app.route(path)
    def homepage(request):
        raise Exception()
        return PlainTextResponse("Hello, world!")

    handler = Mangum(app)
    response = handler(mock_http_event, {})

    assert response == {
        "body": "Error!",
        "headers": {"content-length": "6", "content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_cycle_state(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})
    assert response == {
        "body": "Internal Server Error",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.start", "status": 200})

    handler = Mangum(app, lifespan="off")

    response = handler(mock_http_event, {})
    assert response == {
        "body": "Internal Server Error",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_api_gateway_base_path(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200})

    handler = Mangum(app, lifespan="off", api_gateway_base_path=None)
    assert handler.strip_base_path(mock_http_event["path"]) == urllib.parse.unquote(
        mock_http_event["path"]
    )

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200})

    api_gateway_base_path = "test"
    script_name = "/" + api_gateway_base_path
    handler = Mangum(app, lifespan="off", api_gateway_base_path=api_gateway_base_path)
    assert handler.strip_base_path(mock_http_event["path"]) == urllib.parse.unquote(
        mock_http_event["path"][len(script_name) :]
    )


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_text_mime_types(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(
        app, lifespan="off", text_mime_types=["application/vnd.apple.pkpass"]
    )
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_binary_gzip_response(mock_http_event) -> None:
    body = json.dumps({"abc": "defg"})

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            }
        )

        await send({"type": "http.response.body", "body": body.encode()})

    handler = Mangum(GZipMiddleware(app, minimum_size=1), lifespan="off")
    response = handler(mock_http_event, {})

    assert response["isBase64Encoded"]
    assert response["headers"] == {
        "content-encoding": "gzip",
        "content-type": "application/json",
        "content-length": "35",
        "vary": "Accept-Encoding",
    }
    assert response["body"] == base64.b64encode(gzip.compress(body.encode())).decode()


@pytest.mark.parametrize(
    "mock_http_api_event",
    [
        (["GET", None, None, ""]),
        (["GET", None, {"name": ["me"]}, "name=me"]),
        (["GET", None, {"name": ["me", "you"]}, "name=me&name=you"]),
        (
            [
                "GET",
                None,
                {"name": ["me", "you"], "pet": ["dog"]},
                "name=me&name=you&pet=dog",
            ]
        ),
    ],
    indirect=["mock_http_api_event"],
)
def test_http_request(mock_http_api_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "version": "2.0",
                "routeKey": "$default",
                "rawPath": "/my/path",
                "rawQueryString": mock_http_api_event["rawQueryString"],
                "cookies": ["cookie1", "cookie2"],
                "headers": {
                    "accept-encoding": "gzip,deflate",
                    "x-forwarded-port": "443",
                    "x-forwarded-proto": "https",
                    "host": "test.execute-api.us-west-2.amazonaws.com",
                },
                "queryStringParameters": mock_http_api_event["queryStringParameters"],
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
                        "method": "GET",
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
                "body": None,
                "pathParameters": {"parameter1": "value1"},
                "isBase64Encoded": False,
                "stageVariables": {
                    "stageVariable1": "value1",
                    "stageVariable2": "value2",
                },
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [b"accept-encoding", b"gzip,deflate"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/my/path",
            "query_string": mock_http_api_event["rawQueryString"].encode(),
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_api_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_response_headers(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"x-header-1", b"123"], [b"x-header-2", b"456"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")

    mock_http_event["headers"] = None

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"x-header-1": "123", "x-header-2": "456"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_empty_header(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")

    mock_http_event["headers"] = None

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }
