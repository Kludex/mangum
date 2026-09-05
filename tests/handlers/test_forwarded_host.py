from __future__ import annotations

import pytest

from mangum import Mangum
from mangum.handlers.api_gateway import HTTPGateway
from mangum.handlers.utils import get_server_and_port
from mangum.types import LambdaConfig, LambdaEvent
from tests.context import MockLambdaContext

CONTEXT = MockLambdaContext()

CONFIG = LambdaConfig(api_gateway_base_path="/", text_mime_types=[], exclude_headers=[])


def get_mock_aws_http_gateway_event_v2(headers: dict[str, str]) -> LambdaEvent:
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": headers,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "domainName": "lambda-url.us-east-1.on.aws",
            "domainPrefix": "id",
            "http": {
                "method": "GET",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "IP",
                "userAgent": "agent",
            },
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390,
        },
        "body": None,
        "isBase64Encoded": False,
    }


def test_get_server_and_port_host_fallback() -> None:
    assert get_server_and_port({"host": "mangum.io"}) == ("mangum.io", 80)
    assert get_server_and_port({}) == ("mangum", 80)


def test_get_server_and_port_forwarded_host() -> None:
    headers = {"host": "lambda-url.us-east-1.on.aws", "x-forwarded-host": "example.com"}
    assert get_server_and_port(headers) == ("example.com", 80)
    # The host header is normalized so frameworks that derive absolute URLs
    # from it (e.g. Starlette) don't leak the proxy endpoint.
    assert headers["host"] == "example.com"


def test_get_server_and_port_forwarded_host_with_port() -> None:
    headers = {"host": "lambda-url.us-east-1.on.aws", "x-forwarded-host": "example.com:8443"}
    assert get_server_and_port(headers) == ("example.com", 8443)


def test_aws_http_gateway_scope_forwarded_host_v2() -> None:
    """
    When CloudFront fronts a Lambda Function URL, the original domain is kept
    only in `x-forwarded-host`, while `host` points at the Function URL.
    """
    example_event = get_mock_aws_http_gateway_event_v2(
        {
            "Host": "lambda-url.us-east-1.on.aws",
            "X-Forwarded-Host": "example.com",
        }
    )
    handler = HTTPGateway(example_event, CONTEXT, CONFIG)

    server = handler.scope["server"]
    assert server == ("example.com", 80)


def test_url_for_uses_forwarded_host() -> None:
    """
    Regression test for https://github.com/Kludex/mangum/issues/302: `url_for`
    behind CloudFront + Function URL must use the real domain.
    """
    pytest.importorskip("starlette")
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    async def homepage(request):
        return PlainTextResponse(str(request.url_for("homepage")))

    app = Starlette(routes=[Route("/", homepage)])
    handler = Mangum(app, lifespan="off")
    result = handler(
        get_mock_aws_http_gateway_event_v2(
            {
                "host": "lambda-url.us-east-1.on.aws",
                "x-forwarded-host": "example.com",
                "x-forwarded-proto": "https",
            }
        ),
        CONTEXT,
    )
    assert result["isBase64Encoded"] is False
    assert result["body"] == "https://example.com/"
