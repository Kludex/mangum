import enum
import asyncio
import logging
from dataclasses import dataclass, field

from mangum.websocket import WebSocket
from mangum.exceptions import UnexpectedMessage, WebSocketClosed
from mangum.types import ASGIApp, Message


class WebSocketCycleState(enum.Enum):
    CONNECTING = enum.auto()
    HANDSHAKE = enum.auto()
    RESPONSE = enum.auto()
    DISCONNECTING = enum.auto()
    CLOSED = enum.auto()


@dataclass
class WebSocketCycle:

    body: str
    websocket: WebSocket
    log_level: str
    state: WebSocketCycleState = WebSocketCycleState.CONNECTING
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.websockets")
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.response["statusCode"] = 200

    def __call__(self, app: ASGIApp) -> dict:
        self.logger.debug("WebSocket cycle starting.")
        self.app_queue.put_nowait({"type": "websocket.connect"})
        asgi_instance = self.run(app)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)

        return self.response

    async def run(self, app: ASGIApp) -> None:
        """
        Calls the application with the connection scope and handling error cases.
        """
        try:
            await app(self.websocket.scope, self.receive, self.send)
        except WebSocketClosed:
            self.response["statusCode"] = 403
        except UnexpectedMessage:
            self.response["statusCode"] = 500
        except BaseException as exc:
            self.logger.error("Exception in ASGI application", exc_info=exc)
            self.response["statusCode"] = 500

    async def receive(self) -> Message:
        """
        Awaited by the application to receive ASGI WebSocket events, handling event
        state transitions.
        """
        if self.state is WebSocketCycleState.CONNECTING:

            # Initial ASGI connection established. The next event returned by the queue
            # will be `websocket.connect` to initiate the handshake.
            self.state = WebSocketCycleState.HANDSHAKE

        elif self.state is WebSocketCycleState.HANDSHAKE:

            # ASGI connection handshake accepted. The next event returned by the queue
            # will be `websocket.receive` containing the message data from API Gateway.
            self.state = WebSocketCycleState.RESPONSE

        elif self.state is WebSocketCycleState.RESPONSE:

            # ASGI connection disconnecting. The next event returned by the queue will
            # be `websocket.disconnect` to close the current ASGI connection.
            self.state = WebSocketCycleState.DISCONNECTING

        return await self.app_queue.get()

    async def send(self, message: Message) -> None:
        message_type = message["type"]
        self.logger.info(
            "%s:  '%s' event received from application.", self.state, message_type
        )

        if self.state is WebSocketCycleState.HANDSHAKE and message_type in (
            "websocket.accept",
            "websocket.close",
        ):

            # API Gateway handles the WebSocket client handshake in the connect event,
            # and it cannot be negotiated by the application directly. The handshake
            # behaviour is simulated to allow the application to accept or reject the
            # the client connection. This process does not support subprotocols.
            if message_type == "websocket.accept":
                await self.app_queue.put(
                    {"type": "websocket.receive", "bytes": None, "text": self.body}
                )
            elif message_type == "websocket.close":
                self.state = WebSocketCycleState.CLOSED
                raise WebSocketClosed
        elif (
            self.state is WebSocketCycleState.RESPONSE
            and message_type == "websocket.send"
        ):

            # Message data sent from the application is posted to the WebSocket client
            # in API Gateway using an API call.
            message_text = message.get("text", "")
            self.websocket.post_to_connection(message_text.encode())
            await self.app_queue.put({"type": "websocket.disconnect", "code": "1000"})

        elif (
            self.state is WebSocketCycleState.DISCONNECTING
            and message_type == "websocket.close"
        ):
            # ASGI connection is closing, however the WebSocket client in API Gateway
            # will persist and be used in future application ASGI connections until the
            # client disconnects or the application rejects a handshake.
            self.state = WebSocketCycleState.CLOSED
        else:
            raise UnexpectedMessage(
                f"{self.state}: Unexpected '{message_type}' event received."
            )
