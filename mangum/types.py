import typing

try:
    from typing import Protocol  # python 3.8+
except ImportError:
    from typing_extensions import Protocol as _Protocol  # python 2.7, 3.4-3.7

    Protocol = typing.cast(typing._SpecialForm, _Protocol)
    # Otherwise, Protocol has incompatible type "typing_extensions._SpecialForm"

Message = typing.Dict[str, typing.Any]

Scope = typing.Dict[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]


class ASGIApp(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...  # pragma: no cover
