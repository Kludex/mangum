from dataclasses import dataclass
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
from typing_extensions import Protocol, TypeAlias

QueryParams: TypeAlias = MutableMapping[str, Union[str, Sequence[str]]]
Message: TypeAlias = MutableMapping[str, Any]
Scope: TypeAlias = MutableMapping[str, Any]
Receive: TypeAlias = Callable[[], Awaitable[Message]]
Send: TypeAlias = Callable[[Message], Awaitable[None]]

LambdaEvent = Dict[str, Any]


class LambdaCognitoIdentity:
    """Information about the Amazon Cognito identity that authorized the request.

    **cognito_identity_id** - The authenticated Amazon Cognito identity.
    **cognito_identity_pool_id** - The Amazon Cognito identity pool that authorized the
    invocation.
    """

    cognito_identity_id: str
    cognito_identity_pool_id: str


class LambdaMobileClient:
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


class LambdaMobileClientContext:
    """Information about client application and device when invoked via AWS Mobile SDK.

    **client** - A dict of name-value pairs that describe the mobile client application.
    **custom** - A dict of custom values set by the mobile client application.
    **env** - A dict of environment information provided by the AWS SDK.
    """

    client: LambdaMobileClient
    custom: Dict[str, Any]
    env: Dict[str, Any]


class LambdaContext:
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


class ASGIApp(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...  # pragma: no cover


@dataclass
class BaseRequest:
    """
    A holder for an ASGI scope. Contains additional meta from the event that triggered
    the Lambda function.
    """

    headers: List[List[bytes]]
    path: str
    scheme: str
    query_string: bytes
    server: Tuple[str, int]
    client: Tuple[str, int]

    # Invocation event
    trigger_event: Dict[str, Any]
    trigger_context: Union["LambdaContext", Dict[str, Any]]

    raw_path: Optional[str] = None
    root_path: str = ""

    @property
    def scope(self) -> Scope:
        return {
            "http_version": "1.1",
            "headers": self.headers,
            "path": self.path,
            "raw_path": self.raw_path,
            "root_path": self.root_path,
            "scheme": self.scheme,
            "query_string": self.query_string,
            "server": self.server,
            "client": self.client,
            "asgi": {"version": "3.0"},
            "aws.event": self.trigger_event,
            "aws.context": self.trigger_context,
        }


@dataclass
class Request(BaseRequest):
    """
    A holder for an ASGI scope. Specific for usage with HTTP connections.

    https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope
    """

    type: str = "http"
    method: str = "GET"

    @property
    def scope(self) -> Scope:
        scope = super().scope
        scope.update({"type": self.type, "method": self.method})
        return scope


@dataclass
class Response:
    status: int
    headers: List[List[bytes]]  # ex: [[b'content-type', b'text/plain; charset=utf-8']]
    body: bytes
