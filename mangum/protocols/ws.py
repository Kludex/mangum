import enum
import asyncio
import logging
from dataclasses import dataclass, field

from mangum.websocket import WebSocket
from mangum.types import ASGIApp, Message


class WebSocketCycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class WebSocketCycle:

    websocket: WebSocket
    log_level: str
    state: WebSocketCycleState = WebSocketCycleState.REQUEST
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.asgi.websocket")
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.response["statusCode"] = 200
        self.logger.debug("WebSocket cycle initialized!")

    def __call__(self, app: ASGIApp) -> dict:
        asgi_instance = self.run(app)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)

        return self.response

    async def run(self, app: ASGIApp) -> None:
        try:
            await app(self.websocket.scope, self.receive, self.send)
        except BaseException as exc:
            self.logger.error("Exception in ASGI application", exc_info=exc)
            self.response["statusCode"] = 500

    async def receive(self) -> Message:  # pragma: no cover
        message = await self.app_queue.get()

        return message

    async def send(self, message: Message) -> None:
        if self.state is WebSocketCycleState.REQUEST:
            if message["type"] in ("websocket.accept", "websocket.close"):
                self.state = WebSocketCycleState.RESPONSE
            else:
                raise RuntimeError(
                    f"Expected 'websocket.accept' or 'websocket.close', received: {message['type']}"
                )
        else:
            msg_data = message.get("text", "").encode()
            if message["type"] == "websocket.send":
                self.websocket.post_to_connection(msg_data)
            await self.app_queue.put({"type": "websocket.disconnect", "code": "1000"})

    def put_message(self, message: Message) -> None:
        self.app_queue.put_nowait(message)
