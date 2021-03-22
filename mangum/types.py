from dataclasses import dataclass, field
from typing import (
    List,
    Tuple,
    Dict,
    Any,
    Union,
    Optional,
    MutableMapping,
    Awaitable,
    Callable,
    TYPE_CHECKING,
)
from typing_extensions import Protocol


Message = MutableMapping[str, Any]
Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


if TYPE_CHECKING:  # pragma: no cover
    from awslambdaric.lambda_context import LambdaContext


class ASGIApp(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...  # pragma: no cover


@dataclass
class Request:
    """
    A holder for an ASGI scope. Contains additional meta from the event that triggered
    the

    https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope
    """

    method: str
    headers: List[List[bytes]]
    path: str
    scheme: str
    query_string: bytes
    server: Tuple[str, int]
    client: Tuple[str, int]

    # Invocation event
    trigger_event: Dict[str, Any]
    trigger_context: Union["LambdaContext", Dict[str, Any]]
    event_type: str

    type: str = "http"
    http_version: str = "1.1"
    raw_path: Optional[str] = None
    root_path: str = ""
    asgi: Dict[str, str] = field(default_factory=lambda: {"version": "3.0"})

    @property
    def scope(self) -> Scope:
        return {
            "type": self.type,
            "http_version": self.http_version,
            "method": self.method,
            "headers": self.headers,
            "path": self.path,
            "raw_path": self.raw_path,
            "root_path": self.root_path,
            "scheme": self.scheme,
            "query_string": self.query_string,
            "server": self.server,
            "client": self.client,
            "asgi": self.asgi,
            # Meta data to pass along to the application in case they need it
            "aws.event": self.trigger_event,
            "aws.context": self.trigger_context,
            "aws.eventType": self.event_type,
        }


@dataclass
class Response:
    status: int
    headers: List[List[bytes]]  # ex: [[b'content-type', b'text/plain; charset=utf-8']]
    body: bytes
