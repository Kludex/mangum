import typing
from typing_extensions import Protocol

Message = typing.MutableMapping[str, typing.Any]
ScopeDict = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]


class ASGIApp(Protocol):
    async def __call__(self, scope: ScopeDict, receive: Receive, send: Send) -> None:
        ...  # pragma: no cover
