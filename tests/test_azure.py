import typing
from starlette.applications import Starlette
from starlette.responses import HTMLResponse

from mangum.handlers.azure import azure_handler


class MockHttpRequest:
    def __init__(
        self,
        method: str,
        url: str,
        headers: typing.Optional[typing.Mapping[str, str]] = None,
        params: typing.Optional[typing.Mapping[str, str]] = None,
        route_params: typing.Optional[typing.Mapping[str, str]] = None,
        body: bytes = None,
    ) -> None:
        self.method = method
        self.url = url
        self.headers = headers
        self.params = params
        self.route_params = route_params
        self.body = body

    def get_body(self) -> str:
        return self.body


def test_azure_response() -> None:
    def app(scope):
        async def asgi(receive, send):
            message = await receive()
            if message["type"] == "http.request":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"text/html; charset=utf-8"]],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b"<html><h1>Hello, world!</h1></html>",
                    }
                )

        return asgi

    mock_request = MockHttpRequest(
        "GET",
        "/",
        headers={"content-type": "text/html; charset=utf-8"},
        params={"name": "val"},
        route_params=None,
        body=None,
    )
    response = azure_handler(app, mock_request)

    assert response.status_code == 200
    assert response.headers == {"content-type": "text/html; charset=utf-8"}
    assert response.get_body() == b"<html><h1>Hello, world!</h1></html>"
    assert response.charset == "utf-8"
    assert response.mimetype == "text/html"


def test_azure_response_with_body() -> None:
    def app(scope):
        async def asgi(receive, send):
            message = await receive()
            body = message["body"]
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/html; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": body})

        return asgi

    body = "123"
    mock_request = MockHttpRequest(
        "POST",
        "/",
        headers={"content-type": "text/html; charset=utf-8"},
        params=None,
        route_params=None,
        body=body,
    )

    response = azure_handler(app, mock_request)

    assert response.status_code == 200
    assert response.headers == {"content-type": "text/html; charset=utf-8"}
    assert response.get_body() == b"123"
    assert response.charset == "utf-8"
    assert response.mimetype == "text/html"


def test_starlette_azure_response() -> None:
    app = Starlette()

    @app.route("/")
    def homepage(request):
        return HTMLResponse("<html><h1>Hello, world!</h1></html>")

    mock_request = MockHttpRequest(
        "GET",
        "/",
        headers={"content-type": "text/html; charset=utf-8"},
        params=None,
        route_params=None,
        body=None,
    )

    response = azure_handler(app, mock_request)

    assert response.status_code == 200
    assert response.headers == {
        "content-type": "text/html; charset=utf-8",
        "content-length": "35",
    }
    assert response.get_body() == b"<html><h1>Hello, world!</h1></html>"
    assert response.charset == "utf-8"
    assert response.mimetype == "text/html"
