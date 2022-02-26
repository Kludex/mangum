from __future__ import annotations

from typing import (
    List,
    Tuple,
    Dict,
    Any,
    Union,
    Optional,
    Sequence,
    MutableMapping,
    Awaitable,
    Callable,
)
from typing_extensions import Literal, Protocol, TypedDict, TypeAlias


LambdaEvent = Dict[str, Any]
QueryParams: TypeAlias = MutableMapping[str, Union[str, Sequence[str]]]


class LambdaCognitoIdentity(Protocol):
    """Information about the Amazon Cognito identity that authorized the request.

    **cognito_identity_id** - The authenticated Amazon Cognito identity.
    **cognito_identity_pool_id** - The Amazon Cognito identity pool that authorized the
    invocation.
    """

    cognito_identity_id: str
    cognito_identity_pool_id: str


class LambdaMobileClient(Protocol):
    """Mobile client information for the application and the device.

    **installation_id** - A unique identifier for an installation instance of an
    application.
    **app_title** - The title of the application. For example, "My App".
    **app_version_code** - The version of the application. For example, "V2.0".
    **app_version_name** - The version code for the application. For example, 3.
    **app_package_name** - The name of the package. For example, "com.example.my_app".
    """

    installation_id: str
    app_title: str
    app_version_name: str
    app_version_code: str
    app_package_name: str


class LambdaMobileClientContext(Protocol):
    """Information about client application and device when invoked via AWS Mobile SDK.

    **client** - A dict of name-value pairs that describe the mobile client application.
    **custom** - A dict of custom values set by the mobile client application.
    **env** - A dict of environment information provided by the AWS SDK.
    """

    client: LambdaMobileClient
    custom: Dict[str, Any]
    env: Dict[str, Any]


class LambdaContext(Protocol):
    """The context object passed to the handler function.

    **function_name** - The name of the Lambda function.
    **function_version** - The version of the function.
    **invoked_function_arn** - The Amazon Resource Name (ARN) that's used to invoke the
    function. Indicates if the invoker specified a version number or alias.
    **memory_limit_in_mb** - The amount of memory that's allocated for the function.
    **aws_request_id** - The identifier of the invocation request.
    **log_group_name** - The log group for the function.
    **log_stream_name** - The log stream for the function instance.
    **identity** - (mobile apps) Information about the Amazon Cognito identity that
    authorized the request.
    **client_context** - (mobile apps) Client context that's provided to Lambda by the
    client application.
    """

    function_name: str
    function_version: str
    invoked_function_arn: str
    memory_limit_in_mb: int
    aws_request_id: str
    log_group_name: str
    log_stream_name: str
    identity: Optional[LambdaCognitoIdentity]
    client_context: Optional[LambdaMobileClientContext]

    def get_remaining_time_in_millis(self) -> int:
        """Returns the number of milliseconds left before the execution times out."""
        ...  # pragma: no cover


Headers: TypeAlias = List[List[bytes]]


class HTTPRequestEvent(TypedDict):
    type: Literal["http.request"]
    body: bytes
    more_body: bool


class HTTPDisconnectEvent(TypedDict):
    type: Literal["http.disconnect"]


class HTTPResponseStartEvent(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: Headers


class HTTPResponseBodyEvent(TypedDict):
    type: Literal["http.response.body"]
    body: bytes
    more_body: bool


class LifespanStartupEvent(TypedDict):
    type: Literal["lifespan.startup"]


class LifespanStartupCompleteEvent(TypedDict):
    type: Literal["lifespan.startup.complete"]


class LifespanStartupFailedEvent(TypedDict):
    type: Literal["lifespan.startup.failed"]
    message: str


class LifespanShutdownEvent(TypedDict):
    type: Literal["lifespan.shutdown"]


class LifespanShutdownCompleteEvent(TypedDict):
    type: Literal["lifespan.shutdown.complete"]


class LifespanShutdownFailedEvent(TypedDict):
    type: Literal["lifespan.shutdown.failed"]
    message: str


ASGIReceiveEvent: TypeAlias = Union[
    HTTPRequestEvent,
    HTTPDisconnectEvent,
    LifespanStartupEvent,
    LifespanShutdownEvent,
]

ASGISendEvent: TypeAlias = Union[
    HTTPResponseStartEvent,
    HTTPResponseBodyEvent,
    HTTPDisconnectEvent,
    LifespanStartupCompleteEvent,
    LifespanStartupFailedEvent,
    LifespanShutdownCompleteEvent,
    LifespanShutdownFailedEvent,
]


ASGIReceive: TypeAlias = Callable[[], Awaitable[ASGIReceiveEvent]]
ASGISend: TypeAlias = Callable[[ASGISendEvent], Awaitable[None]]


class ASGISpec(TypedDict):
    spec_version: Literal["2.0"]
    version: Literal["3.0"]


HTTPScope = TypedDict(
    "HTTPScope",
    {
        "type": Literal["http"],
        "asgi": ASGISpec,
        "http_version": Literal["1.1"],
        "scheme": str,
        "method": str,
        "path": str,
        "raw_path": None,
        "root_path": Literal[""],
        "query_string": bytes,
        "headers": Headers,
        "client": Tuple[str, int],
        "server": Tuple[str, int],
        "aws.event": LambdaEvent,
        "aws.context": LambdaContext,
    },
)


class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    asgi: ASGISpec


LifespanMode: TypeAlias = Literal["auto", "on", "off"]
Scope: TypeAlias = Union[HTTPScope, LifespanScope]


class ASGIApp(Protocol):
    async def __call__(
        self, scope: Scope, receive: ASGIReceive, send: ASGISend
    ) -> None:
        ...  # pragma: no cover


class HTTPResponse(TypedDict):
    status: int
    headers: Headers
    body: bytes


class LambdaConfig(TypedDict):
    api_gateway_base_path: str


class LambdaHandler(Protocol):
    @classmethod
    def infer(
        cls, event: LambdaEvent, context: LambdaContext, config: LambdaConfig
    ) -> Optional[LambdaHandler]:
        ...  # pragma: no cover

    def __init__(
        self, event: LambdaEvent, context: LambdaContext, config: LambdaConfig
    ) -> None:
        ...  # pragma: no cover

    @property
    def body(self) -> bytes:
        ...  # pragma: no cover

    @property
    def scope(self) -> HTTPScope:
        ...  # pragma: no cover

    def __call__(self, response: HTTPResponse) -> dict:
        ...  # pragma: no cover
