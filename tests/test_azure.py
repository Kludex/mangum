import typing
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
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


def test_asgi_response() -> None:
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

    mock_request = MockHttpRequest(
        "GET",
        "/",
        headers={"content-type": "text/plain; charset=utf-8"},
        params={"name": "val"},
        route_params=None,
        body=None,
    )
    response = azure_handler(App, mock_request)

    assert response == {"status_code": 200, "body": "Hello, world!"}


def test_starlette_response() -> None:

    app = Starlette()

    @app.route("/")
    def homepage(request):
        return PlainTextResponse("Hello, world!")

    mock_request = MockHttpRequest(
        "GET",
        "/",
        headers={"content-type": "text/plain; charset=utf-8"},
        params=None,
        route_params=None,
        body=None,
    )

    response = azure_handler(app, mock_request)

    assert response == {"status_code": 200, "body": "Hello, world!"}
