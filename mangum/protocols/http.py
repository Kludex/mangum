import enum
import asyncio
from typing import Optional
import logging
from io import BytesIO
from dataclasses import dataclass

from .. import Response, Request
from ..types import ASGIApp, Message
from ..exceptions import UnexpectedMessage


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

    * **request** - A request object containing the event and context for the connection
    scope used to run the ASGI application instance.
    * **state** - An enumerated `HTTPCycleState` type that indicates the state of the
    ASGI connection.
    * **app_queue** - An asyncio queue (FIFO) containing messages to be received by the
    application.
    * **response** - A dictionary containing the response data to return in AWS Lambda.
    """

    request: Request
    state: HTTPCycleState = HTTPCycleState.REQUEST
    response: Optional[Response] = None

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.http")
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.body: BytesIO = BytesIO()

    def __call__(self, app: ASGIApp, initial_body: bytes) -> Response:
        self.logger.debug("HTTP cycle starting.")
        self.app_queue.put_nowait(
            {"type": "http.request", "body": initial_body, "more_body": False}
        )
        asgi_instance = self.run(app)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)

        if self.response is None:
            # Something really bad happened and we puked before we could get a
            # response out
            self.response = Response(
                status=500,
                body=b"Internal Server Error",
                headers=[[b"content-type", b"text/plain; charset=utf-8"]],
            )
        return self.response

    async def run(self, app: ASGIApp) -> None:
        """
        Calls the application with the `http` connection scope.
        """
        try:
            await app(self.request.scope, self.receive, self.send)
        except BaseException as exc:
            self.logger.error("Exception in 'http' protocol.", exc_info=exc)
            if self.state is HTTPCycleState.REQUEST:
                await self.send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                    }
                )
                await self.send(
                    {"type": "http.response.body", "body": b"Internal Server Error"}
                )
            elif self.state is not HTTPCycleState.COMPLETE:
                self.response = Response(
                    status=500,
                    body=b"Internal Server Error",
                    headers=[[b"content-type", b"text/plain; charset=utf-8"]],
                )

    async def receive(self) -> Message:
        """
        Awaited by the application to receive ASGI `http` events.
        """
        return await self.app_queue.get()  # pragma: no cover

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
            if self.response is None:
                self.response = Response(
                    status=message["status"],
                    headers=message.get("headers", []),
                    body=b"",
                )
            self.state = HTTPCycleState.RESPONSE
        elif (
            self.state is HTTPCycleState.RESPONSE
            and message_type == "http.response.body"
        ):
            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            # The body must be completely read before returning the response.
            self.body.write(body)

            if not more_body and self.response is not None:
                body = self.body.getvalue()
                self.body.close()
                self.response.body = body

                self.state = HTTPCycleState.COMPLETE
                await self.app_queue.put({"type": "http.disconnect"})

        else:
            raise UnexpectedMessage(
                f"{self.state}: Unexpected '{message_type}' event received."
            )
