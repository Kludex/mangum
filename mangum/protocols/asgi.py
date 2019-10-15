import enum
import asyncio
import base64
import typing
from dataclasses import dataclass, field

from mangum.types import ASGIScope, ASGIMessage, ASGIApp


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class ASGICycle:

    scope: ASGIScope
    state: ASGICycleState = ASGICycleState.REQUEST
    binary: bool = False
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.app_queue = asyncio.Queue(loop=self.loop)

    def __call__(self, app: ASGIApp) -> typing.Dict[str, typing.Any]:
        asgi_instance = app(self.scope, self.asgi_receive, self.asgi_send)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)
        return self.response

    async def asgi_receive(self) -> ASGIMessage:
        message = await self.app_queue.get()
        return message

    def put_message(self, message: ASGIMessage) -> None:
        self.app_queue.put_nowait(message)
