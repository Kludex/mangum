import base64
import enum
import asyncio
import typing
import cgi
import logging
from dataclasses import dataclass, field

from mangum.types import ASGIApp, Message, Scope


class HTTPCycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()
    COMPLETE = enum.auto()


@dataclass
class HTTPCycle:

    scope: Scope
    text_mime_types: typing.List[str]
    log_level: str
    state: HTTPCycleState = HTTPCycleState.REQUEST
    body: bytes = b""
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.asgi.http")
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.response["isBase64Encoded"] = False
        self.logger.debug("HTTP cycle initialized!")

    def __call__(self, app: ASGIApp) -> dict:
        asgi_instance = self.run(app)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)

        return self.response

    async def run(self, app: ASGIApp) -> None:
        try:
            await app(self.scope, self.receive, self.send)
        except BaseException as exc:
            self.logger.error("Exception in ASGI application", exc_info=exc)
            if self.state is HTTPCycleState.REQUEST:
                await self.send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                    }
                )
                await self.send(
                    {"type": "http.response.body", "body": b"Internal Server Error"}
                )
                self.state = HTTPCycleState.COMPLETE

            elif self.state is not HTTPCycleState.COMPLETE:
                self.response["statusCode"] = 500
                self.response["body"] = "Internal Server Error"
                self.response["headers"] = {"content-type": "text/plain; charset=utf-8"}

    async def receive(self) -> Message:
        message = await self.app_queue.get()

        return message

    async def send(self, message: Message) -> None:
        self.logger.debug("New message event %s received.", message["type"])
        if self.state is HTTPCycleState.REQUEST:
            if message["type"] != "http.response.start":
                raise RuntimeError(
                    f"Expected 'http.response.start', received: {message['type']}"
                )

            status_code = message["status"]
            headers = {k: v for k, v in message.get("headers", [])}
            self.response["statusCode"] = status_code

            self.response["headers"] = {
                k.decode(): v.decode() for k, v in headers.items()
            }
            self.state = HTTPCycleState.RESPONSE

        elif self.state is HTTPCycleState.RESPONSE:
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
                mimetype, _ = cgi.parse_header(
                    self.response["headers"].get("content-type", "text/plain")
                )
                response_is_binary = (
                    mimetype not in self.text_mime_types
                    and not mimetype.startswith("text/")
                ) or self.response["headers"].get("content-encoding") == "gzip"
                if response_is_binary:
                    body = base64.b64encode(body)
                    self.response["isBase64Encoded"] = True

                self.response["body"] = body.decode()
                self.put_message({"type": "http.disconnect"})
                self.state = HTTPCycleState.COMPLETE

    def put_message(self, message: Message) -> None:
        self.app_queue.put_nowait(message)
