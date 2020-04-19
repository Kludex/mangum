import sys

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

from mangum import Mangum

# One (or more) of Quart's dependencies does not support Python 3.8, ignore this case.
IS_PY38 = sys.version_info[:2] == (3, 8)
IS_PY36 = sys.version_info[:2] == (3, 6)

if not (IS_PY38 or IS_PY36):
    from quart import Quart
else:
    Quart = None


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_lifespan_startup_error(mock_http_event) -> None:
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    raise Exception("error")
        else:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app)
    assert handler.lifespan.is_supported
    assert handler.lifespan.has_error

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_lifespan(mock_http_event) -> None:
    startup_complete = False
    shutdown_complete = False

    async def app(scope, receive, send):
        nonlocal startup_complete, shutdown_complete

        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                    startup_complete = True
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    shutdown_complete = True
                    return
        else:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app)
    assert startup_complete

    response = handler(mock_http_event, {})
    assert shutdown_complete
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_lifespan_unsupported(mock_http_event) -> None:
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app)
    assert not handler.lifespan.is_supported

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_lifespan_disabled(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
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


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_lifespan_supported_with_error(mock_http_event) -> None:
    async def app(scope, receive, send):
        await receive()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app)
    assert handler.lifespan.is_supported
    assert handler.lifespan.has_error

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_starlette_lifespan(mock_http_event) -> None:
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


@pytest.mark.skipif(
    IS_PY38, reason="One (or more) of Quart's dependencies does not support Python 3.8."
)
@pytest.mark.skipif(IS_PY36, reason="Quart does not support Python 3.6.")
@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_quart_lifespan(mock_http_event) -> None:
    startup_complete = False
    shutdown_complete = False
    path = mock_http_event["path"]
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
