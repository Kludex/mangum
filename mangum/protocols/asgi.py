import enum
import asyncio
import base64
import typing
from dataclasses import dataclass, field

from mangum.types import ASGIScope, ASGIMessage, ASGIApp, AWSMessage


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class ASGICycle:

    scope: ASGIScope
    state: ASGICycleState = ASGICycleState.REQUEST
    binary: bool = False
    response: AWSMessage = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue(loop=self.loop)

    def __call__(self, app: ASGIApp) -> AWSMessage:
        asgi_instance = app(self.scope, self.asgi_receive, self.asgi_send)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)
        return self.response

    async def asgi_receive(self) -> ASGIMessage:
        message = await self.app_queue.get()
        return message

    async def asgi_send(self, message: ASGIMessage) -> None:  # pragma: no cover
        raise NotImplementedError

    def put_message(self, message: ASGIMessage) -> None:
        self.app_queue.put_nowait(message)
