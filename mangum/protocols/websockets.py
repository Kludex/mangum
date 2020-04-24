import enum
import asyncio
from dataclasses import dataclass, field

from mangum.connections import WebSocket
from mangum.exceptions import WebSocketError
from mangum.types import ASGIApp, Message


class WebSocketCycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class WebSocketCycle:
    websocket: WebSocket
    state: WebSocketCycleState = WebSocketCycleState.REQUEST
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.response["statusCode"] = 200

    def __call__(self, app: ASGIApp) -> dict:
        asgi_instance = app(self.websocket.scope, self.receive, self.send)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)

        return self.response

    async def run(self, app: ASGIApp) -> None:
        try:
            await app(self.scope, self.receive, self.send)
        except BaseException as exc:
            msg = "Exception in ASGI application\n"
            self.logger.error(msg, exc_info=exc)
            if self.state is not WebSocketCycleState.COMPLETE:
                self.state = WebSocketCycleState.COMPLETE
            self.response["statusCode"] = 500

    async def receive(self) -> Message:
        message = await self.app_queue.get()

        return message

    async def send(self, message: Message) -> None:
        if self.state is WebSocketCycleState.REQUEST:
            if message["type"] in ("websocket.accept", "websocket.close"):
                self.state = WebSocketCycleState.RESPONSE
            else:
                raise WebSocketError(
                    f"Expected 'websocket.accept' or 'websocket.close', received: {message['type']}"
                )
        else:
            data = message.get("text", "")
            if message["type"] == "websocket.send":
                self.websocket.send(data)
