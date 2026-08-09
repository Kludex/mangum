from __future__ import annotations

from typing import Any

from mangum import Mangum
from mangum.protocols import HTTPCycle
from mangum.types import Cycle, Headers, LambdaConfig, LambdaContext, LambdaEvent, Response, Scope


class CustomHandler:
    @classmethod
    def infer(cls, event: LambdaEvent, context: LambdaContext, config: LambdaConfig) -> bool:
        return "my-custom-key" in event

    def __init__(self, event: LambdaEvent, context: LambdaContext, config: LambdaConfig) -> None:
        self.event = event
        self.context = context
        self.config = config

    @property
    def body(self) -> bytes:
        return b"My request body"

    @property
    def scope(self) -> Scope:
        headers: dict[str, str] = {}
        return {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "headers": [[k.encode(), v.encode()] for k, v in headers.items()],
            "path": "/",
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "query_string": b"",
            "server": ("mangum", 8080),
            "client": ("127.0.0.1", 0),
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "aws.event": self.event,
            "aws.context": self.context,
        }

    def __call__(self, *, status: int, headers: Headers, body: bytes) -> dict[str, Any]:
        return {"statusCode": status, "headers": {}, "body": body.decode()}


def test_custom_handler():
    event = {"my-custom-key": 1}
    handler = CustomHandler(event, {}, {"api_gateway_base_path": "/"})
    assert isinstance(handler.body, bytes)
    assert handler.scope == {
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "aws.context": {},
        "aws.event": event,
        "client": ("127.0.0.1", 0),
        "headers": [],
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "raw_path": None,
        "root_path": "",
        "scheme": "https",
        "server": ("mangum", 8080),
        "type": "http",
    }


def test_custom_handler_infer():
    """Test the infer method of CustomHandler."""
    event_with_key = {"my-custom-key": 1}
    event_without_key = {"other-key": 1}

    assert CustomHandler.infer(event_with_key, {}, {"api_gateway_base_path": "/"}) is True
    assert CustomHandler.infer(event_without_key, {}, {"api_gateway_base_path": "/"}) is False


def test_custom_handler_call():
    """Test the __call__ method of CustomHandler."""
    event = {"my-custom-key": 1}
    handler = CustomHandler(event, {}, {"api_gateway_base_path": "/"})

    result = handler(status=200, headers=[], body=b"Hello, World!")
    assert result == {"statusCode": 200, "headers": {}, "body": "Hello, World!"}


def test_custom_handler_with_custom_cycle_cls():
    """Test that a handler can define a custom cycle_cls property."""

    class HandlerWithCustomCycle:
        @classmethod
        def infer(cls, event, context, config):
            return "custom-cycle" in event

        def __init__(self, event, context, config):
            self.event = event
            self.context = context
            self.config = config

        @property
        def cycle_cls(self) -> type[Cycle]:
            return HTTPCycle

        @property
        def body(self) -> bytes:
            return b""

        @property
        def scope(self) -> Scope:
            return {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "headers": [],
                "path": "/",
                "raw_path": None,
                "root_path": "",
                "scheme": "https",
                "query_string": b"",
                "server": ("localhost", 8080),
                "client": ("127.0.0.1", 0),
                "asgi": {"version": "3.0", "spec_version": "2.0"},
                "aws.event": self.event,
                "aws.context": self.context,
            }

        def __call__(self, response: Response) -> dict:
            return {"statusCode": response["status"], "body": response["body"].decode()}

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    handler = Mangum(app, lifespan="off", custom_handlers=[HandlerWithCustomCycle])
    response = handler({"custom-cycle": True}, {})

    assert response["statusCode"] == 200
    assert response["body"] == "OK"
