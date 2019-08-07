import base64
import pytest
from mangum import Mangum


@pytest.mark.parametrize("mock_http_event", [["GET", None]], indirect=True)
def test_http_response(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        assert scope == {
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
            "query_string": b"name=me",
            "raw_path": None,
            "root_path": "Prod",
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

    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "123"]], indirect=True)
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

    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "456123",
    }


@pytest.mark.parametrize(
    "mock_http_event", [["GET", base64.b64encode(b"123")]], indirect=True
)
def test_http_binary_response__with_body(mock_http_event) -> None:
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
    handler = Mangum(app, enable_lifespan=False)
    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": base64.b64encode(b"123").decode(),
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None]], indirect=True)
def test_http_event_debug(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        raise Exception("Error!")
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, enable_lifespan=False, debug=True)
    response = handler(mock_http_event, {})

    assert response["statusCode"] == 500
    assert not response["isBase64Encoded"]
    assert response["headers"] == {"content-type": "text/plain; charset=utf-8"}
    assert response["body"].split()[0] == "Traceback"


@pytest.mark.parametrize("mock_http_event", [["GET", ""]], indirect=True)
def test_http_cycle_state(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, enable_lifespan=False)

    with pytest.raises(RuntimeError):
        handler(mock_http_event, {})

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.start", "status": 200, "headers": []})

    handler = Mangum(app, enable_lifespan=False)
    with pytest.raises(RuntimeError):
        handler(mock_http_event, {})