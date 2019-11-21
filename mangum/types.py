import typing

try:  # python 3.8+
    from typing import Protocol
except ImportError:  # python 2.7, 3.4-3.7
    from typing_extensions import Protocol as _Protocol

    Protocol = typing.cast(typing._SpecialForm, _Protocol)
    # Otherwise, Protocol has incompatible type "typing_extensions._SpecialForm"

Message = typing.Dict[str, typing.Any]

Scope = typing.Dict[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]


class ASGIApp(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...
