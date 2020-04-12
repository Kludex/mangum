import base64
import enum
import logging
import asyncio
import typing
import cgi
from dataclasses import dataclass, field

from mangum.types import ASGIApp, Message, Scope


class ASGIState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()
    COMPLETE = enum.auto()


@dataclass
class ASGIHTTPCycle:

    scope: Scope
    logger: logging.Logger
    text_mime_types: typing.List[str]
    state: ASGIState = ASGIState.REQUEST
    body: bytes = b""
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.response["isBase64Encoded"] = False

    def __call__(self, app: ASGIApp) -> dict:
        asgi_instance = self.run(app)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)
        return self.response

    async def run(self, app: ASGIApp) -> None:
        try:
            await app(self.scope, self.receive, self.send)
        except BaseException as exc:
            msg = "Exception in ASGI application\n"
            self.logger.error(msg, exc_info=exc)
            if self.state is ASGIState.REQUEST:
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
                self.state = ASGIState.COMPLETE

            elif self.state is not ASGIState.COMPLETE:
                self.response["statusCode"] = 500
                self.response["body"] = "Internal Server Error"
                self.response["headers"] = {"content-type": "text/plain; charset=utf-8"}

    async def receive(self) -> Message:
        message = await self.app_queue.get()
        return message

    async def send(self, message: Message) -> None:
        if self.state is ASGIState.REQUEST:
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
                self.state = ASGIState.COMPLETE

    def put_message(self, message: Message) -> None:
        self.app_queue.put_nowait(message)
