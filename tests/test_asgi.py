import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from quart import Quart
from mangum import Mangum


def test_asgi_cycle_state(mock_data) -> None:
    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.body", "body": b"Hello, world!"})

        return asgi

    mock_event = mock_data.get_aws_event()
    with pytest.raises(RuntimeError):
        Mangum(app)(mock_event, {})

    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.start", "status": 200, "headers": []})

        return asgi

    mock_event = mock_data.get_aws_event()
    with pytest.raises(RuntimeError):
        Mangum(app)(mock_event, {})


def test_asgi_spec_version(mock_data) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    mock_event = mock_data.get_aws_event()
    mock_event["body"] = None
    handler = Mangum(app, spec_version=3)
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {},
        "body": "Hello, world!",
    }


def test_starlette_response(mock_data) -> None:
    mock_event = mock_data.get_aws_event()

    app = Starlette()

    @app.route(mock_event["path"])
    def homepage(request):
        return PlainTextResponse("Hello, world!")

    handler = Mangum(app, spec_version=3)
    mock_event["body"] = None
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {
            "content-length": "13",
            "content-type": "text/plain; charset=utf-8",
        },
        "body": "Hello, world!",
    }


def test_quart_response(mock_data) -> None:
    mock_event = mock_data.get_aws_event()
    mock_event["body"] = None

    app = Quart(__name__)

    @app.route(mock_event["path"])
    async def hello():
        return "hello world!"

    handler = Mangum(app)
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-length": "12", "content-type": "text/html; charset=utf-8"},
        "body": "hello world!",
    }
