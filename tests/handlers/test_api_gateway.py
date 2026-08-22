import urllib.parse

import httpx2
import pytest

from mangum import Mangum
from mangum.handlers.api_gateway import APIGateway
from mangum.types import LambdaConfig, LambdaEvent, QueryParams, Receive, Scope, Send
from tests.context import MockLambdaContext

CONTEXT = MockLambdaContext()

CONFIG = LambdaConfig(api_gateway_base_path="/", text_mime_types=[], exclude_headers=[])


def get_mock_aws_api_gateway_event(
    method: str,
    path: str,
    multi_value_query_parameters: QueryParams | None,
    body: str | bytes | None,
    body_base64_encoded: bool,
) -> LambdaEvent:
    event: LambdaEvent = {
        "path": path,
        "body": body,
        "isBase64Encoded": body_base64_encoded,
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
            "Cookie": "cookie1; cookie2",
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
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
                "user": "",
            },
            "resourcePath": "/{proxy+}",
            "httpMethod": method,
            "apiId": "123",
        },
        "resource": "/{proxy+}",
        "httpMethod": method,
        "multiValueQueryStringParameters": (
            {k: v for k, v in multi_value_query_parameters.items()} if multi_value_query_parameters else None
        ),
        "stageVariables": {"stageVarName": "stageVarValue"},
    }
    return event


def test_aws_api_gateway_scope_basic() -> None:
    """
    Test the event from the AWS docs
    """
    example_event = {
        "resource": "/",
        "path": "/",
        "httpMethod": "GET",
        "requestContext": {"resourcePath": "/", "httpMethod": "GET", "path": "/Prod/"},
        "headers": {
            "accept": "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "Host": "70ixmpl4fl.execute-api.us-east-2.amazonaws.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/80.0.3987.132 Safari/537.36",
            "X-Amzn-Trace-Id": "Root=1-5e66d96f-7491f09xmpl79d18acf3d050",
        },
        "multiValueHeaders": {
            "accept": [
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,image/apng,*/*;q=0.8,"
                "application/signed-exchange;v=b3;q=0.9"
            ],
            "accept-encoding": ["gzip, deflate, br"],
        },
        "queryStringParameters": {"foo": "bar"},
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "body": None,
        "isBase64Encoded": False,
    }
    example_context = CONTEXT
    handler = APIGateway(example_event, example_context, CONFIG)

    assert isinstance(handler.body, bytes)
    assert handler.scope == {
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "aws.context": CONTEXT,
        "aws.event": example_event,
        "client": (None, 0),
        "headers": [
            [
                b"accept",
                b"text/html,application/xhtml+xml,application/xml;"
                b"q=0.9,image/webp,image/apng,*/*;q=0.8,"
                b"application/signed-exchange;v=b3;q=0.9",
            ],
            [b"accept-encoding", b"gzip, deflate, br"],
            [b"host", b"70ixmpl4fl.execute-api.us-east-2.amazonaws.com"],
            [
                b"user-agent",
                b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                b"AppleWebKit/537.36 (KHTML, like Gecko) "
                b"Chrome/80.0.3987.132 "
                b"Safari/537.36",
            ],
            [b"x-amzn-trace-id", b"Root=1-5e66d96f-7491f09xmpl79d18acf3d050"],
        ],
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "query_string": b"foo=bar",
        "raw_path": None,
        "root_path": "",
        "scheme": "https",
        "server": ("70ixmpl4fl.execute-api.us-east-2.amazonaws.com", 80),
        "type": "http",
    }


@pytest.mark.parametrize(
    "method,path,multi_value_query_parameters,req_body,body_base64_encoded,query_string,scope_body",
    [
        ("GET", "/hello/world", None, None, False, b"", None),
        (
            "POST",
            "/",
            {"name": ["me"]},
            "field1=value1&field2=value2",
            False,
            b"name=me",
            b"field1=value1&field2=value2",
        ),
        (
            "GET",
            "/my/resource",
            {"name": ["me", "you"]},
            None,
            False,
            b"name=me&name=you",
            None,
        ),
        (
            "GET",
            "",
            {"name": ["me", "you"], "pet": ["dog"]},
            None,
            False,
            b"name=me&name=you&pet=dog",
            None,
        ),
        # A 1x1 red px gif
        (
            "POST",
            "/img",
            None,
            b"R0lGODdhAQABAIABAP8AAAAAACwAAAAAAQABAAACAkQBADs=",
            True,
            b"",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\xff\x00\x00\x00\x00\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
        ),
        ("POST", "/form-submit", None, b"say=Hi&to=Mom", False, b"", b"say=Hi&to=Mom"),
    ],
)
def test_aws_api_gateway_scope_real(
    method: str,
    path: str,
    multi_value_query_parameters: QueryParams | None,
    req_body: str | bytes | None,
    body_base64_encoded: bool,
    query_string: bytes,
    scope_body: bytes | None,
) -> None:
    event = get_mock_aws_api_gateway_event(method, path, multi_value_query_parameters, req_body, body_base64_encoded)
    example_context = CONTEXT
    handler = APIGateway(event, example_context, CONFIG)

    scope_path = path
    if scope_path == "":
        scope_path = "/"

    assert handler.scope == {
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "aws.context": CONTEXT,
        "aws.event": event,
        "client": ("192.168.100.1", 0),
        "headers": [
            [
                b"accept",
                b"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            ],
            [b"accept-encoding", b"gzip, deflate, lzma, sdch, br"],
            [b"accept-language", b"en-US,en;q=0.8"],
            [b"cloudfront-forwarded-proto", b"https"],
            [b"cloudfront-is-desktop-viewer", b"true"],
            [b"cloudfront-is-mobile-viewer", b"false"],
            [b"cloudfront-is-smarttv-viewer", b"false"],
            [b"cloudfront-is-tablet-viewer", b"false"],
            [b"cloudfront-viewer-country", b"US"],
            [b"cookie", b"cookie1; cookie2"],
            [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
            [b"upgrade-insecure-requests", b"1"],
            [b"x-forwarded-for", b"192.168.100.1, 192.168.1.1"],
            [b"x-forwarded-port", b"443"],
            [b"x-forwarded-proto", b"https"],
        ],
        "http_version": "1.1",
        "method": method,
        "path": scope_path,
        "query_string": query_string,
        "raw_path": None,
        "root_path": "",
        "scheme": "https",
        "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
        "type": "http",
    }

    if handler.body:
        assert handler.body == scope_body
    else:
        assert handler.body == b""


@pytest.mark.parametrize(
    "method,path,multi_value_query_parameters,req_body,body_base64_encoded,query_string,scope_body",
    [
        ("GET", "/test/hello", None, None, False, b"", None),
    ],
)
def test_aws_api_gateway_base_path(
    method: str,
    path: str,
    multi_value_query_parameters: QueryParams | None,
    req_body: str | bytes | None,
    body_base64_encoded: bool,
    query_string: bytes,
    scope_body: bytes | None,
) -> None:
    event = get_mock_aws_api_gateway_event(method, path, multi_value_query_parameters, req_body, body_base64_encoded)

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "http"
        assert scope["path"] == urllib.parse.unquote(event["path"])
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello world!"})

    handler = Mangum(app, lifespan="off", api_gateway_base_path="/")
    response = handler(event, CONTEXT)

    assert response == {
        "body": "Hello world!",
        "headers": {"content-type": "text/plain"},
        "multiValueHeaders": {},
        "isBase64Encoded": False,
        "statusCode": 200,
    }

    async def app_with_base_path(scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "http"
        assert scope["path"] == urllib.parse.unquote(event["path"][len(f"/{api_gateway_base_path}") :])
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello world!"})

    api_gateway_base_path = "test"
    handler = Mangum(app_with_base_path, lifespan="off", api_gateway_base_path=api_gateway_base_path)
    response = handler(event, CONTEXT)
    assert response == {
        "body": "Hello world!",
        "headers": {"content-type": "text/plain"},
        "multiValueHeaders": {},
        "isBase64Encoded": False,
        "statusCode": 200,
    }


@pytest.mark.parametrize(
    "method,content_type,raw_res_body,res_body,res_base64_encoded",
    [
        ("GET", b"text/plain; charset=utf-8", b"Hello world", "Hello world", False),
        # A 1x1 red px gif
        (
            "POST",
            b"image/gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\xff\x00\x00\x00\x00\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            "R0lGODdhAQABAIABAP8AAAAAACwAAAAAAQABAAACAkQBADs=",
            True,
        ),
    ],
)
def test_aws_api_gateway_response(
    method: str, content_type: bytes, raw_res_body: bytes, res_body: str, res_base64_encoded: bool
) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", content_type]],
            }
        )
        await send({"type": "http.response.body", "body": raw_res_body})

    event = get_mock_aws_api_gateway_event(method, "/test", {}, None, False)

    handler = Mangum(app, lifespan="off")

    response = handler(event, CONTEXT)
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": res_base64_encoded,
        "headers": {"content-type": content_type.decode()},
        "multiValueHeaders": {},
        "body": res_body,
    }


def test_aws_api_gateway_response_extra_mime_types() -> None:
    content_type = b"application/x-yaml"
    utf_res_body = "name: 'John Doe'"
    raw_res_body = utf_res_body.encode()
    b64_res_body = "bmFtZTogJ0pvaG4gRG9lJw=="

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", content_type]],
            }
        )
        await send({"type": "http.response.body", "body": raw_res_body})

    event = get_mock_aws_api_gateway_event("POST", "/test", {}, None, False)

    # Test default behavior
    handler = Mangum(app, lifespan="off")
    response = handler(event, CONTEXT)
    assert content_type.decode() not in handler.config["text_mime_types"]
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {"content-type": content_type.decode()},
        "multiValueHeaders": {},
        "body": b64_res_body,
    }

    # Test with modified text mime types
    handler = Mangum(app, lifespan="off")
    handler.config["text_mime_types"].append(content_type.decode())
    response = handler(event, CONTEXT)
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": content_type.decode()},
        "multiValueHeaders": {},
        "body": utf_res_body,
    }


def test_aws_api_gateway_exclude_headers() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/plain; charset=utf-8"],
                    [b"x-custom-header", b"test"],
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello world"})

    event = get_mock_aws_api_gateway_event("GET", "/test", {}, None, False)

    handler = Mangum(app, lifespan="off", exclude_headers=["X-CUSTOM-HEADER"])

    response = handler(event, CONTEXT)
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": b"text/plain; charset=utf-8".decode()},
        "multiValueHeaders": {},
        "body": "Hello world",
    }


def test_aws_api_gateway_real_lambda_get(rest_api_url: str) -> None:
    response = httpx2.get(f"{rest_api_url}test/path", params={"hello": "world"}, timeout=60)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-echo"] == "mangum"
    assert response.json() == {
        "method": "GET",
        "path": "/test/path",
        "query": "hello=world",
        "body_length": 0,
        "lifespan_startup_complete": True,
    }


def test_aws_api_gateway_real_lambda_post(rest_api_url: str) -> None:
    response = httpx2.post(f"{rest_api_url}submit", content=b"say=Hi&to=Mom", timeout=60)

    assert response.status_code == 200
    assert response.json() == {
        "method": "POST",
        "path": "/submit",
        "query": "",
        "body_length": 13,
        "lifespan_startup_complete": True,
    }
