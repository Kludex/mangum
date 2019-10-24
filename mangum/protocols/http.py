import urllib.parse
import base64
import typing
import enum
import asyncio
from dataclasses import dataclass, field

from mangum.types import ASGIApp, Message, Scope
from mangum.utils import get_server_and_client


class ASGIState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class ASGIHTTPCycle:

    scope: Scope
    state: ASGIState = ASGIState.REQUEST
    binary: bool = False
    body: bytes = b""
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue(loop=self.loop)

    def __call__(self, app: ASGIApp) -> dict:
        asgi_instance = app(self.scope, self.asgi_receive, self.asgi_send)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)
        return self.response

    async def asgi_receive(self) -> Message:
        message = await self.app_queue.get()
        return message

    async def asgi_send(self, message: Message) -> None:
        if self.state is ASGIState.REQUEST:
            if message["type"] != "http.response.start":
                raise RuntimeError(
                    f"Expected 'http.response.start', received: {message['type']}"
                )

            status_code = message["status"]
            headers = {k: v for k, v in message.get("headers", [])}
            self.response["statusCode"] = status_code
            self.response["isBase64Encoded"] = self.binary
            self.response["headers"] = {
                k.decode(): v.decode() for k, v in headers.items()
            }
            self.state = ASGIState.RESPONSE

        elif self.state is ASGIState.RESPONSE:
            if message["type"] != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message['type']}"
                )

            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            # The body must be completely read before returning the response.
            self.body += body

            if not more_body:
                body = self.body
                if self.binary:
                    body = base64.b64encode(body)
                self.response["body"] = body.decode()
                self.put_message({"type": "http.disconnect"})

    def put_message(self, message: Message) -> None:
        self.app_queue.put_nowait(message)


def handle_http(app: ASGIApp, event: dict, context: dict) -> dict:
    server, client = get_server_and_client(event)
    headers = [[k.lower().encode(), v.encode()] for k, v in event["headers"].items()]
    query_string_params = event["queryStringParameters"]
    query_string = (
        urllib.parse.urlencode(query_string_params).encode()
        if query_string_params
        else b""
    )
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": event["httpMethod"],
        "headers": headers,
        "path": urllib.parse.unquote(event["path"]),
        "raw_path": None,
        "root_path": "",
        "scheme": event["headers"].get("X-Forwarded-Proto", "https"),
        "query_string": query_string,
        "server": server,
        "client": client,
        # "aws": {"event": event, "context": context},
    }
    binary = event.get("isBase64Encoded", False)
    body = event["body"] or b""
    if binary:
        body = base64.b64decode(body)
    elif not isinstance(body, bytes):
        body = body.encode()

    asgi_cycle = ASGIHTTPCycle(scope, binary=binary)
    asgi_cycle.put_message({"type": "http.request", "body": body, "more_body": False})
    response = asgi_cycle(app)

    return response
