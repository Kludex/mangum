import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from quart import Quart
from mangum import Mangum


def test_asgi_cycle_state(mock_data) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    mock_event = mock_data.get_aws_event()
    handler = Mangum(app, enable_lifespan=False)

    with pytest.raises(RuntimeError):
        handler(mock_event, {})

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.start", "status": 200, "headers": []})

    mock_event = mock_data.get_aws_event()
    handler = Mangum(app, enable_lifespan=False)
    with pytest.raises(RuntimeError):
        handler(mock_event, {})


def test_asgi_spec_version(mock_data) -> None:
    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"Hello, world!"})

        return asgi

    mock_event = mock_data.get_aws_event()
    mock_event["body"] = None
    handler = Mangum(app, spec_version=2, enable_lifespan=False)
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {},
        "body": "Hello, world!",
    }


def test_starlette_response(mock_data) -> None:
    mock_event = mock_data.get_aws_event()
    startup_complete = False
    shutdown_complete = False

    app = Starlette()

    @app.on_event("startup")
    async def on_startup():
        nonlocal startup_complete
        startup_complete = True

    @app.on_event("shutdown")
    async def on_shutdown():
        nonlocal shutdown_complete
        shutdown_complete = True

    @app.route(mock_event["path"])
    def homepage(request):
        return PlainTextResponse("Hello, world!")

    assert not startup_complete
    assert not shutdown_complete

    handler = Mangum(app)
    mock_event["body"] = None

    assert startup_complete
    assert not shutdown_complete

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
    assert startup_complete
    assert shutdown_complete


def test_quart_app(mock_data) -> None:
    mock_event = mock_data.get_aws_event()

    startup_complete = False
    shutdown_complete = False

    app = Quart(__name__)
    mock_event["body"] = None

    @app.before_serving
    async def on_startup():
        nonlocal startup_complete
        startup_complete = True

    @app.after_serving
    async def on_shutdown():
        nonlocal shutdown_complete
        shutdown_complete = True

    @app.route(mock_event["path"])
    async def hello():
        return "hello world!"

    assert not startup_complete
    assert not shutdown_complete

    handler = Mangum(app)

    assert startup_complete
    assert not shutdown_complete

    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-length": "12", "content-type": "text/html; charset=utf-8"},
        "body": "hello world!",
    }
    assert startup_complete
    assert shutdown_complete
