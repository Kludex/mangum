import pytest
from mangum.handlers.asgi import ASGICycle
from starlette.responses import PlainTextResponse


class MockASGICycle(ASGICycle):
    def on_response_start(self, headers: list, status_code: int) -> None:
        self.response["status"] = status_code

    def on_response_body(self, body: str) -> None:
        self.response["body"] = body


def mock_asgi_handler(app, event: dict) -> dict:
    scope = {
        "type": "http",
        "server": None,
        "client": None,
        "scheme": "https",
        "root_path": "",
        "query_string": "",
        "headers": [],
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
    }
    body = event.get("body", b"")
    handler = MockASGICycle(scope, body=body)
    return handler(app)


def test_asgi_handler() -> None:
    def app(scope):
        async def asgi(receive, send):
            res = PlainTextResponse("Hello, world!")
            await res(receive, send)

        return asgi

    mock_request = {}
    response = mock_asgi_handler(app, mock_request)

    assert response == {"status": 200, "body": b"Hello, world!"}


def test_asgi_cycle_state() -> None:
    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.body", "body": b"Hello, world!"})

        return asgi

    with pytest.raises(RuntimeError):
        mock_asgi_handler(app, {})

    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.start", "status": 200, "headers": []})

        return asgi

    with pytest.raises(RuntimeError):
        mock_asgi_handler(app, {})
