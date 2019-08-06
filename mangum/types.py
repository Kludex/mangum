import typing

ASGIScope = typing.Dict[str, typing.Any]
ASGIMessage = typing.Dict[str, typing.Any]
ASGIReceive = typing.Callable[[], typing.Awaitable[ASGIMessage]]
ASGISend = typing.Callable[[ASGIMessage], typing.Awaitable[None]]
ASGIApp = typing.Callable[[ASGIScope, ASGIReceive, ASGISend], typing.Awaitable[None]]
AWSEvent = typing.Dict[str, str]
AWSContext = typing.Dict[str, str]
AWSResponse = typing.Dict[str, str]
