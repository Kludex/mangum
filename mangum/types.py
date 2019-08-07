import typing

ASGIScope = typing.Dict[str, typing.Any]
ASGIMessage = typing.Dict[str, typing.Any]
ASGIReceive = typing.Callable[[], typing.Awaitable[ASGIMessage]]
ASGISend = typing.Callable[[ASGIMessage], typing.Awaitable[None]]
ASGIApp = typing.Callable[[ASGIScope, ASGIReceive, ASGISend], typing.Awaitable[None]]
