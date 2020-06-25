import base64
import enum
import asyncio
import typing
import cgi
import logging
from dataclasses import dataclass, field

from mangum.types import ASGIApp, Message, Scope
from mangum.exceptions import UnexpectedMessage


class HTTPCycleState(enum.Enum):
    """
    The state of the ASGI `http` connection.

    * **REQUEST** - Initial state. The ASGI application instance will be run with the
    connection scope containing the `http` type.
    * **RESPONSE** - The `http.response.start` event has been sent by the application.
    The next expected message is the `http.response.body` event, containing the body
    content. An application may pass the `more_body` argument to send content in chunks,
    however content will always be returned in a single response, never streamed.
    * **COMPLETE** - The body content from the ASGI application has been completely
    read. A disconnect event will be sent to the application, and the response will
    be returned.
    """

    REQUEST = enum.auto()
    RESPONSE = enum.auto()
    COMPLETE = enum.auto()


@dataclass
class HTTPCycle:
    """
    Manages the application cycle for an ASGI `http` connection.

    * **scope** - A dictionary containing the connection scope used to run the ASGI
    application instance.
    * **body** -  A byte string containing the body content of the request.
    * **text_mime_types** - A list of mime types of MIME types that should not return
    a binary response in API Gateway.
    * **state** - An enumerated `HTTPCycleState` type that indicates the state of the
    ASGI connection.
    * **app_queue** - An asyncio queue (FIFO) containing messages to be received by the
    application.
    * **response** - A dictionary containing the response data to return in AWS Lambda.
    """

    scope: Scope
    body: bytes
    text_mime_types: typing.List[str]
    state: HTTPCycleState = HTTPCycleState.REQUEST
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.http")
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.response["isBase64Encoded"] = False

    def __call__(self, app: ASGIApp) -> dict:
        self.logger.debug("HTTP cycle starting.")
        self.app_queue.put_nowait(
            {"type": "http.request", "body": self.body, "more_body": False}
        )
        self.body = b""
        asgi_instance = self.run(app)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)

        return self.response

    async def run(self, app: ASGIApp) -> None:
        """
        Calls the application with the `http` connection scope.
        """
        try:
            await app(self.scope, self.receive, self.send)
        except BaseException as exc:
            self.logger.error("Exception in 'http' protocol.", exc_info=exc)
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
            elif self.state is not HTTPCycleState.COMPLETE:
                self.response["statusCode"] = 500
                self.response["body"] = "Internal Server Error"
                self.response["headers"] = {"content-type": "text/plain; charset=utf-8"}

    async def receive(self) -> Message:
        """
        Awaited by the application to receive ASGI `http` events.
        """
        return await self.app_queue.get()

    async def send(self, message: Message) -> None:
        """
        Awaited by the application to send ASGI `http` events.
        """
        message_type = message["type"]
        self.logger.info(
            "%s:  '%s' event received from application.", self.state, message_type
        )

        if (
            self.state is HTTPCycleState.REQUEST
            and message_type == "http.response.start"
        ):
            self.response["statusCode"] = message["status"]
            headers: typing.Dict[str, str] = {}
            multi_value_headers: typing.Dict[str, typing.List[str]] = {}
            for key, value in message.get("headers", []):
                lower_key = key.decode().lower()
                if lower_key in multi_value_headers:
                    multi_value_headers[lower_key].append(value.decode())
                elif lower_key in headers:
                    multi_value_headers[lower_key] = [
                        headers.pop(lower_key),
                        value.decode(),
                    ]
                else:
                    headers[lower_key] = value.decode()

            self.response["headers"] = headers
            if multi_value_headers:
                self.response["multiValueHeaders"] = multi_value_headers
            self.state = HTTPCycleState.RESPONSE

        elif (
            self.state is HTTPCycleState.RESPONSE
            and message_type == "http.response.body"
        ):
            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            # The body must be completely read before returning the response.
            self.body += body

            if not more_body:
                body = self.body

                # Check if a binary response should be returned based on the mime type
                # or content encoding.
                mimetype, _ = cgi.parse_header(
                    self.response["headers"].get("content-type", "text/plain")
                )
                if (
                    mimetype not in self.text_mime_types
                    and not mimetype.startswith("text/")
                ) or self.response["headers"].get("content-encoding") == "gzip":
                    body = base64.b64encode(body)
                    self.response["isBase64Encoded"] = True

                self.response["body"] = body.decode()
                self.state = HTTPCycleState.COMPLETE
                await self.app_queue.put({"type": "http.disconnect"})

        else:
            raise UnexpectedMessage(
                f"{self.state}: Unexpected '{message_type}' event received."
            )
