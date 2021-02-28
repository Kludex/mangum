import enum
import typing
from typing_extensions import Protocol

Message = typing.MutableMapping[str, typing.Any]
Scope = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]


class ASGIApp(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...  # pragma: no cover


class EventSource(enum.Enum):
    ALB = enum.auto()
    ALB_MULTIVALUEHEADERS = enum.auto()
    API_GW_V1 = enum.auto()
    API_GW_V2 = enum.auto()

    @classmethod
    def get_event_source(cls, event: dict) -> "EventSource":
        version_val = event.get("version", None)
        multi_value_headers_val = event.get("multiValueHeaders", None)
        if version_val == "1.0":
            return cls.API_GW_V1
        elif version_val == "2.0":
            return cls.API_GW_V2
        elif multi_value_headers_val is not None:
            return cls.ALB_MULTIVALUEHEADERS
        else:
            return cls.ALB
