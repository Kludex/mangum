import pytest
from mangum.handlers.asgi import ASGIHandler, ASGICycle

from starlette.requests import ClientDisconnect, Request
from starlette.responses import JSONResponse, Response
from starlette.testclient import TestClient


class MockASGICycle(ASGICycle):
    def on_response_start(self, headers: list, status_code: int) -> None:
        self.response["status"] = status_code

    def on_response_body(self, body: str) -> None:
        self.response["body"] = body


class MockASGIHandler(ASGIHandler):
    asgi_cycle_class = MockASGICycle


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
    more_body = False
    message = {"type": "http.request", "body": body, "more_body": more_body}
    handler = MockASGIHandler(scope)

    return handler(app, message)


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


# def test_asgi_request_body():
#     class App:
#         def __init__(self, scope) -> None:
#             self.scope = scope

#         async def __call__(self, receive, send) -> None:

#             message = await receive()

#             body = message["body"]
#             more_body = False

#             await send(
#                 {
#                     "type": "http.response.start",
#                     "status": 200,
#                     "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
#                 }
#             )
#             await send(
#                 {
#                     "type": "http.response.start",
#                     "status": 200,
#                     "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
#                 }
#             )


def test_request_body():
    def app(scope):
        async def asgi(receive, send):
            request = Request(scope, receive)
            body = await request.body()
            response = JSONResponse({"body": body.decode()})
            await response(receive, send)

        return asgi

    mock_request = {"body": b"123"}
    response = mock_asgi_handler(app, mock_request)
    print(response)
