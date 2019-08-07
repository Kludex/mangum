import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from quart import Quart
from mangum import Mangum


@pytest.mark.parametrize("mock_http_event", [["GET", None]], indirect=True)
def test_starlette_response(mock_http_event) -> None:
    startup_complete = False
    shutdown_complete = False

    path = mock_http_event["path"]

    app = Starlette()

    @app.on_event("startup")
    async def on_startup():
        nonlocal startup_complete
        startup_complete = True

    @app.on_event("shutdown")
    async def on_shutdown():
        nonlocal shutdown_complete
        shutdown_complete = True

    @app.route(path)
    def homepage(request):
        return PlainTextResponse("Hello, world!")

    assert not startup_complete
    assert not shutdown_complete

    handler = Mangum(app)
    mock_http_event["body"] = None

    assert startup_complete
    assert not shutdown_complete

    response = handler(mock_http_event, {})

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


@pytest.mark.parametrize("mock_http_event", [["GET", None]], indirect=True)
def test_quart_app(mock_http_event) -> None:
    path = mock_http_event["path"]
    startup_complete = False
    shutdown_complete = False

    app = Quart(__name__)

    @app.before_serving
    async def on_startup():
        nonlocal startup_complete
        startup_complete = True

    @app.after_serving
    async def on_shutdown():
        nonlocal shutdown_complete
        shutdown_complete = True

    @app.route(path)
    async def hello():
        return "hello world!"

    assert not startup_complete
    assert not shutdown_complete

    handler = Mangum(app)

    assert startup_complete
    assert not shutdown_complete

    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-length": "12", "content-type": "text/html; charset=utf-8"},
        "body": "hello world!",
    }
    assert startup_complete
    assert shutdown_complete
