import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal, cast

import pytest
from quart import Quart
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mangum import Mangum
from mangum.exceptions import LifespanFailure
from mangum.types import ASGI, LambdaEvent, LifespanMode, Receive, Scope, Send
from tests.context import MockLambdaContext

CONTEXT = MockLambdaContext()


@pytest.mark.parametrize(
    "mock_aws_api_gateway_event,lifespan",
    [
        (["GET", None, None], "auto"),
        (["GET", None, None], "on"),
        (["GET", None, None], "off"),
    ],
    indirect=["mock_aws_api_gateway_event"],
)
def test_lifespan(mock_aws_api_gateway_event: LambdaEvent, lifespan: LifespanMode) -> None:
    """
    Test each lifespan option using an application that supports lifespan messages.

    * "auto" (default):
        Application support for lifespan will be inferred.

        Any error that occurs during startup will be logged and the ASGI application
        cycle will continue unless a `lifespan.startup.failed` event is sent.

    * "on":
        Application support for lifespan is explicit.

        Any error that occurs during startup will be raised and a 500 response will
        be returned.

    * "off":
        Application support for lifespan should be ignored.

        The application will not enter the lifespan cycle context.
    """
    startup_complete = False
    shutdown_complete = False

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
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

        if scope["type"] == "http":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan=lifespan)
    response = handler(mock_aws_api_gateway_event, CONTEXT)
    expected = lifespan in ("on", "auto")

    assert startup_complete == expected
    assert shutdown_complete == expected
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "multiValueHeaders": {},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_aws_api_gateway_event,lifespan",
    [
        (["GET", None, None], "auto"),
        (["GET", None, None], "on"),
        (["GET", None, None], "off"),
    ],
    indirect=["mock_aws_api_gateway_event"],
)
def test_lifespan_unsupported(mock_aws_api_gateway_event: LambdaEvent, lifespan: LifespanMode) -> None:
    """
    Test each lifespan option with an application that does not support lifespan events.
    """

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan=lifespan)
    response = handler(mock_aws_api_gateway_event, CONTEXT)

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "multiValueHeaders": {},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_aws_api_gateway_event,lifespan",
    [(["GET", None, None], "auto"), (["GET", None, None], "on")],
    indirect=["mock_aws_api_gateway_event"],
)
def test_lifespan_error(
    mock_aws_api_gateway_event: LambdaEvent, lifespan: LifespanMode, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.ERROR)

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
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

    handler = Mangum(app, lifespan=lifespan)
    response = handler(mock_aws_api_gateway_event, CONTEXT)

    assert "Exception in 'lifespan' protocol." in caplog.text
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "multiValueHeaders": {},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_aws_api_gateway_event,lifespan",
    [(["GET", None, None], "auto"), (["GET", None, None], "on")],
    indirect=["mock_aws_api_gateway_event"],
)
def test_lifespan_unexpected_message(mock_aws_api_gateway_event: LambdaEvent, lifespan: LifespanMode) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 200,
                            "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                        }
                    )

    handler = Mangum(app, lifespan=lifespan)
    with pytest.raises(LifespanFailure):
        handler(mock_aws_api_gateway_event, CONTEXT)


@pytest.mark.parametrize(
    "mock_aws_api_gateway_event,lifespan,failure_type",
    [
        (["GET", None, None], "auto", "startup"),
        (["GET", None, None], "on", "startup"),
        (["GET", None, None], "auto", "shutdown"),
        (["GET", None, None], "on", "shutdown"),
    ],
    indirect=["mock_aws_api_gateway_event"],
)
def test_lifespan_failure(mock_aws_api_gateway_event: LambdaEvent, lifespan: LifespanMode, failure_type: str) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    if failure_type == "startup":
                        await send({"type": "lifespan.startup.failed", "message": "Failed."})
                    else:
                        await send({"type": "lifespan.startup.complete"})
                if message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.failed", "message": "Failed."})

    handler = Mangum(app, lifespan=lifespan)

    with pytest.raises(LifespanFailure):
        handler(mock_aws_api_gateway_event, CONTEXT)


@pytest.mark.parametrize(
    "mock_aws_api_gateway_event,lifespan",
    [(["GET", None, None], "auto"), (["GET", None, None], "on")],
    indirect=["mock_aws_api_gateway_event"],
)
def test_lifespan_state(mock_aws_api_gateway_event: LambdaEvent, lifespan: Literal["on", "auto"]) -> None:
    startup_complete = False
    shutdown_complete = False

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal startup_complete, shutdown_complete

        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    scope["state"].update({"test_key": b"Hello, world!"})
                    await send({"type": "lifespan.startup.complete"})
                    startup_complete = True
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    shutdown_complete = True
                    return

        if scope["type"] == "http":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": scope["state"]["test_key"]})

    handler = Mangum(app, lifespan=lifespan)
    response = handler(mock_aws_api_gateway_event, CONTEXT)

    assert startup_complete
    assert shutdown_complete
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "multiValueHeaders": {},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_aws_api_gateway_event", [["GET", None, None]], indirect=True)
def test_starlette_lifespan(mock_aws_api_gateway_event: LambdaEvent) -> None:
    startup_complete = False
    shutdown_complete = False

    path = mock_aws_api_gateway_event["path"]

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        nonlocal startup_complete, shutdown_complete
        startup_complete = True
        yield
        shutdown_complete = True

    def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("Hello, world!")

    app = Starlette(lifespan=lifespan, routes=[Route(path, homepage)])

    assert not startup_complete
    assert not shutdown_complete

    handler = Mangum(app)
    mock_aws_api_gateway_event["body"] = None

    response = handler(mock_aws_api_gateway_event, CONTEXT)
    assert startup_complete
    assert shutdown_complete
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {
            "content-length": "13",
            "content-type": "text/plain; charset=utf-8",
        },
        "multiValueHeaders": {},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_aws_api_gateway_event", [["GET", None, None]], indirect=True)
def test_quart_lifespan(mock_aws_api_gateway_event: LambdaEvent) -> None:
    startup_complete = False
    shutdown_complete = False
    path = mock_aws_api_gateway_event["path"]
    app = Quart(__name__)

    @app.before_serving
    async def on_startup() -> None:
        nonlocal startup_complete
        startup_complete = True

    @app.after_serving
    async def on_shutdown() -> None:
        nonlocal shutdown_complete
        shutdown_complete = True

    @app.route(path)
    async def hello() -> str:
        return "hello world!"

    assert not startup_complete
    assert not shutdown_complete

    handler = Mangum(cast("ASGI", app))
    response = handler(mock_aws_api_gateway_event, CONTEXT)

    assert startup_complete
    assert shutdown_complete
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-length": "12", "content-type": "text/html; charset=utf-8"},
        "multiValueHeaders": {},
        "body": "hello world!",
    }
