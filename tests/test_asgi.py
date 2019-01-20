import pytest
from mangum.handlers.asgi import ASGICycle


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
    class App:
        def __init__(self, scope) -> None:
            self.scope = scope

        async def __call__(self, receive, send) -> None:
            message = await receive()
            if message["type"] == "http.request":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                    }
                )
                await send({"type": "http.response.body", "body": b"Hello, world!"})

    mock_request = {}
    response = mock_asgi_handler(App, mock_request)

    assert response == {"status": 200, "body": "Hello, world!"}


def test_asgi_request_state() -> None:
    class App:
        def __init__(self, scope) -> None:
            self.scope = scope

        async def __call__(self, receive, send) -> None:
            await send({"type": "http.response.body", "body": b"Hello, world!"})

    mock_request = {}
    with pytest.raises(RuntimeError):
        mock_asgi_handler(App, mock_request)


def test_asgi_response_state() -> None:
    class App:
        def __init__(self, scope) -> None:
            self.scope = scope

        async def __call__(self, receive, send) -> None:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )

    mock_request = {}
    with pytest.raises(RuntimeError):
        mock_asgi_handler(App, mock_request)
