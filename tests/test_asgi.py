import pytest
from mangum.asgi.protocol import ASGICycle
from mangum.asgi.adapter import ServerlessAdapter
from starlette.responses import PlainTextResponse


class MockASGICycle(ASGICycle):
    def on_response_start(self, headers: list, status_code: int) -> None:
        self.response["status"] = status_code

    def on_response_body(self, body: str) -> None:
        self.response["body"] = body


class MockServerlessAdapter(ServerlessAdapter):
    def asgi(self, event: dict) -> dict:
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
        return handler(self.app)


class MockServerlessAdapterWithOptions(MockServerlessAdapter):
    def _debug(self, content: str, status_code: int = 500) -> dict:
        return {"body": content, "status_code": status_code}


def test_serverless_adapter() -> None:
    def app(scope):
        async def asgi(receive, send):
            res = PlainTextResponse("Hello, world!")
            await res(receive, send)

        return asgi

    mock_request = {}
    response = MockServerlessAdapter(app)(mock_request)

    assert response == {"status": 200, "body": b"Hello, world!"}


def test_asgi_cycle_state() -> None:
    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.body", "body": b"Hello, world!"})

        return asgi

    with pytest.raises(RuntimeError):
        MockServerlessAdapter(app)({})

    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.start", "status": 200, "headers": []})

        return asgi

    with pytest.raises(RuntimeError):
        MockServerlessAdapter(app)({})


def test_serverless_adapter_not_implemented() -> None:
    def app(scope):
        async def asgi(receive, send):
            res = PlainTextResponse("Hello, world!")
            await res(receive, send)

        return asgi

    mock_request = {}
    with pytest.raises(NotImplementedError):
        ServerlessAdapter(app)(mock_request)

    def app(scope):
        async def asgi(receive, send):
            res = PlainTextResponse("Hello, world!")
            raise Exception("Not implemented.")
            await res(receive, send)

        return asgi

    mock_request = {}
    with pytest.raises(NotImplementedError):
        MockServerlessAdapter(app, debug=True)(mock_request)


def test_serverless_adapter_debug() -> None:
    def app(scope):
        async def asgi(receive, send):
            res = PlainTextResponse("Hello, world!")
            raise Exception("There was an error!")
            await res(receive, send)

        return asgi

    mock_request = {}
    response = MockServerlessAdapterWithOptions(app, debug=True)(mock_request)
    assert response == {"body": "There was an error!", "status_code": 500}
