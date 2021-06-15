import enum
import asyncio
import logging
from io import BytesIO
from dataclasses import dataclass

from mangum.backends import WebSocket
from mangum.exceptions import UnexpectedMessage, WebSocketClosed
from mangum.types import ASGIApp, Message, Request, Response


class WebSocketCycleState(enum.Enum):
    """
    The state of the ASGI WebSocket connection.

    * **CONNECTING** - Initial state. The ASGI application instance will be run with the
    connection scope containing the `websocket` type.
    * **HANDSHAKE** - The ASGI `websocket` connection with the application has been
    established, and a `websocket.connect` event has been pushed to the application
    queue. The application will respond by accepting or rejecting the connection.
    If rejected, a 403 response will be returned to the client, and it will be removed
    from API Gateway.
    * **RESPONSE** - Handshake accepted by the application. Data received in the API
    Gateway message event will be sent to the application. A `websocket.receive` event
    will be pushed to the application queue.
    * **DISCONNECTING** - The ASGI connection cycle is complete and should be
    disconnected from the application. A `websocket.disconnect` event will be pushed to
    the queue, and a response will be returned to the client connection.
    * **CLOSED** - The application has sent a `websocket.close` message. This will
    either be in response to a `websocket.disconnect` event or occurs when a connection
    is rejected in response to a `websocket.connect` event.
    """

    CONNECTING = enum.auto()
    HANDSHAKE = enum.auto()
    RESPONSE = enum.auto()
    DISCONNECTING = enum.auto()
    CLOSED = enum.auto()


@dataclass
class WebSocketCycle:
    """
    Manages the application cycle for an ASGI `websocket` connection.

    * **websocket** - A `WebSocket` connection handler interface for the selected
    `WebSocketBackend` subclass. Contains the ASGI connection `scope` and client
    connection identifier.
    * **state** - An enumerated `WebSocketCycleState` type that indicates the state of
    the ASGI connection.
    * **app_queue** - An asyncio queue (FIFO) containing messages to be received by the
    application.
    * **response** - A dictionary containing the response data to return in AWS Lambda.
    This will only contain a `statusCode` for WebSocket connections.
    """

    websocket: WebSocket
    request: Request
    message_type: str
    state: WebSocketCycleState = WebSocketCycleState.CONNECTING
    response: Response = Response(200, [], b"")

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.websocket")
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.body: BytesIO = BytesIO()

    def __call__(self, app: ASGIApp, initial_body: bytes) -> Response:
        self.logger.debug("WebSocket cycle starting.")
        self.initial_body = initial_body

        if self.message_type == "CONNECT":
            # loop = asyncio.get_event_loop()
            self.loop.run_until_complete(self.websocket.on_connect(self.request.scope))
        elif self.message_type == "DISCONNECT":
            # loop = asyncio.get_event_loop()
            self.loop.run_until_complete(self.websocket.on_disconnect())
        elif self.message_type == "MESSAGE":
            self.app_queue.put_nowait({"type": "websocket.connect"})
            asgi_instance = self.run(app)
            asgi_task = self.loop.create_task(asgi_instance)
            self.loop.run_until_complete(asgi_task)

        return self.response

    async def run(self, app: ASGIApp) -> None:
        """
        Calls the application with the `websocket` connection scope.
        """
        self.scope = await self.websocket.on_message()
        scope = self.scope.copy()
        try:
            await app(scope, self.receive, self.send)
        except WebSocketClosed:
            self.response.status = 403
        except UnexpectedMessage:
            self.response.status = 500
        except BaseException as exc:
            self.logger.error("Exception in ASGI application", exc_info=exc)
            self.response.status = 500

    async def receive(self) -> Message:
        """
        Awaited by the application to receive ASGI `websocket` events.
        """
        if self.state is WebSocketCycleState.CONNECTING:

            # Initial ASGI connection established. The next event returned by the queue
            # will be `websocket.connect` to initiate the handshake.
            self.state = WebSocketCycleState.HANDSHAKE

        elif self.state is WebSocketCycleState.HANDSHAKE:

            # ASGI connection handshake accepted. The next event returned by the queue
            # will be `websocket.receive` containing the message data from API Gateway.
            self.state = WebSocketCycleState.RESPONSE

        return await self.app_queue.get()

    async def send(self, message: Message) -> None:
        """
        Awaited by the application to send ASGI `websocket` events.
        """
        message_type = message["type"]
        self.logger.info(
            "%s:  '%s' event received from application.", self.state, message_type
        )

        if self.state is WebSocketCycleState.HANDSHAKE and message_type in (
            "websocket.accept",
            "websocket.close",
        ):

            # API Gateway handles the WebSocket client handshake in the connect event,
            # and it cannot be negotiated by the application directly. The application
            # may choose to close the connection at this point. This process does not
            # support subprotocols.
            if message_type == "websocket.accept":
                # TODO Handle text/bytes payload
                await self.app_queue.put(
                    {
                        "type": "websocket.receive",
                        "bytes": self.initial_body,
                        "text": None,
                    }
                )
            elif message_type == "websocket.close":
                self.state = WebSocketCycleState.CLOSED
                await self.websocket.delete_connection()
                raise WebSocketClosed

        elif (
            self.state is WebSocketCycleState.RESPONSE
            and message_type == "websocket.close"
        ):

            # The application is explicitly closing the connection. It should be
            # disconnected and removed in API Gateway.
            await self.websocket.delete_connection()

        elif (
            self.state is WebSocketCycleState.RESPONSE
            and message_type == "websocket.send"
        ):

            # The application requested to send some data in response to the
            # "websocket.receive" event. After it's sent, a "websocket.disconnect"
            # event is generated to let the application finish gracefully.
            # Then the lambda's execution is ended.

            # TODO what if the client sends a binary payload ?
            message_text = message.get("text", "")
            body = message_text.encode()

            await self.websocket.post_to_connection(body=body)
            await self.app_queue.put({"type": "websocket.disconnect", "code": 1000})

        else:
            raise UnexpectedMessage(
                f"{self.state}: Unexpected '{message_type}' event received."
            )