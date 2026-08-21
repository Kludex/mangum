from __future__ import annotations

from typing import Any

from mangum import Mangum
from mangum.types import LambdaConfig, LambdaContext, LambdaEvent, Receive, Response, Scope, Send
from tests.context import MockLambdaContext

CONTEXT = MockLambdaContext()

CONFIG = LambdaConfig(api_gateway_base_path="/", text_mime_types=[], exclude_headers=[])


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

    def __call__(self, response: Response) -> dict[str, Any]:
        return {"statusCode": response["status"], "headers": {}, "body": response["body"].decode()}


def test_custom_handler() -> None:
    event = {"my-custom-key": 1}

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["aws.event"] == event
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"Hello!"})

    handler = Mangum(app, lifespan="off", custom_handlers=[CustomHandler])
    response = handler(event, CONTEXT)

    assert response == {"statusCode": 200, "headers": {}, "body": "Hello!"}


def test_custom_handler_scope() -> None:
    event = {"my-custom-key": 1}
    handler = CustomHandler(event, CONTEXT, CONFIG)
    assert isinstance(handler.body, bytes)
    assert handler.scope == {
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "aws.context": CONTEXT,
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
