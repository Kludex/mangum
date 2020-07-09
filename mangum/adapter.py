import base64
import typing
import logging
import urllib.parse


import warnings
from dataclasses import dataclass, InitVar
from contextlib import ExitStack

from mangum.types import ASGIApp
from mangum.protocols.lifespan import LifespanCycle
from mangum.protocols.http import HTTPCycle
from mangum.exceptions import ConfigurationError


DEFAULT_TEXT_MIME_TYPES = [
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
]


def get_logger(log_level: str) -> logging.Logger:
    """
    Create the default logger according to log level setting of the adapter instance.
    """
    level = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }[log_level]
    logging.basicConfig(
        format="[%(asctime)s] %(message)s", level=level, datefmt="%d-%b-%y %H:%M:%S"
    )
    logger = logging.getLogger("mangum")
    logger.setLevel(level)

    return logger


D = typing.TypeVar('D')

@dataclass
class Mangum:
    """
    Creates an adapter instance.

    * **app** - An asynchronous callable that conforms to version 3.0 of the ASGI
    specification. This will usually be an ASGI framework application instance.
    * **lifespan** - A string to configure lifespan support. Choices are `auto`, `on`,
    and `off`. Default is `auto`.
    * **log_level** - A string to configure the log level. Choices are: `info`,
    `critical`, `error`, `warning`, and `debug`. Default is `info`.
    * **api_gateway_base_path** - Base path to strip from URL when using a custom
    domain name.
    * **text_mime_types** - A list of MIME types to include with the defaults that
    should not return a binary response in API Gateway.
    """

    app: ASGIApp
    lifespan: str = "auto"
    log_level: str = "info"
    api_gateway_base_path: typing.Optional[str] = None
    text_mime_types: typing.Optional[typing.List[str]] = None
    enable_lifespan: InitVar[bool] = True  # Deprecated.

    def __post_init__(self, enable_lifespan: bool) -> None:
        if not enable_lifespan:  # pragma: no cover
            warnings.warn(
                "The `enable_lifespan` parameter will be removed in a future release. "
                "It is replaced by `lifespan` setting.",
                DeprecationWarning,
                stacklevel=2,
            )
        if self.lifespan not in ("auto", "on", "off"):  # pragma: no cover
            raise ConfigurationError(
                "Invalid argument supplied for `lifespan`. Choices are: auto|on|off"
            )

        if self.log_level not in ("critical", "error", "warning", "info", "debug"):
            raise ConfigurationError(  # pragma: no cover
                "Invalid argument supplied for `log_level`. "
                "Choices are: critical|error|warning|info|debug"
            )
        if self.api_gateway_base_path:
            self.api_gateway_base_path = f"/{self.api_gateway_base_path}"
        if self.text_mime_types:
            self.text_mime_types = self.text_mime_types + DEFAULT_TEXT_MIME_TYPES
        else:
            self.text_mime_types = DEFAULT_TEXT_MIME_TYPES

        self.logger: logging.Logger = get_logger(self.log_level)

    @staticmethod
    def get_header(headers: typing.Dict[str, typing.List[str]], key: str, default:D=None) -> typing.Union[str, D]:
        values = headers.get(key, [])
        return (
            values[0]
            if len(values) > 0
            else default
        )

    def __call__(self, event: dict, context: dict) -> dict:
        self.logger.debug("Event received.")

        use_multi_value_headers = False

        with ExitStack() as stack:
            if self.lifespan != "off":
                asgi_cycle: typing.ContextManager = LifespanCycle(
                    self.app, self.lifespan
                )
                stack.enter_context(asgi_cycle)

            request_context = event["requestContext"]
            if "http" in request_context:
                source_ip = request_context["http"]["sourceIp"]
                path = request_context["http"]["path"]
                http_method = request_context["http"]["method"]
                query_string = event.get("rawQueryString", "").encode()
            else:
                source_ip = request_context.get("identity", {}).get("sourceIp")
                multi_value_query_string_params = {}
                if event.get("multiValueQueryStringParameters"):
                    use_multi_value_headers = True
                    multi_value_query_string_params = event.get("multiValueQueryStringParameters")
                elif event.get("queryStringParameters"):
                    multi_value_query_string_params = {k:[v] for k, v in event.get("queryStringParameters").items()}

                query_string = (
                    urllib.parse.urlencode(
                        multi_value_query_string_params, doseq=True
                    ).encode()
                    if multi_value_query_string_params
                    else b""
                )
                path = event["path"]
                http_method = event["httpMethod"]

            headers: typing.Dict[str, typing.List[str]] = {}
            if event.get("headers"):
                headers.update({k.lower(): [v] for k, v in event["headers"].items()})
            if event.get("multiValueHeaders"):
                use_multi_value_headers = True
                headers.update({k.lower(): vv for k, vv in event["multiValueHeaders"].items()})

            server_name = self.get_header(headers, "host", default="mangum")
            if ":" not in server_name:
                server_port = self.get_header(headers, "x-forwarded-port", default="80")
            else:
                server_name, server_port = server_name.split(":")  # pragma: no cover
            server = (server_name, int(server_port))
            client = (source_ip, 0)

            if not path:  # pragma: no cover
                path = "/"
            elif self.api_gateway_base_path:
                if path.startswith(self.api_gateway_base_path):
                    path = path[len(self.api_gateway_base_path) :]

            scope = {
                "type": "http",
                "http_version": "1.1",
                "method": http_method,
                "headers": [
                    [k.encode(), v.encode()]
                    for k, vv in headers.items()
                    for v in vv
                ],
                "path": urllib.parse.unquote(path),
                "raw_path": None,
                "root_path": "",
                "scheme": self.get_header(headers, "x-forwarded-proto", default="https"),
                "query_string": query_string,
                "server": server,
                "client": client,
                "asgi": {"version": "3.0"},
                "aws.event": event,
                "aws.context": context,
            }

            is_binary = event.get("isBase64Encoded", False)
            body = event.get("body") or b""
            if is_binary:
                body = base64.b64decode(body)
            elif not isinstance(body, bytes):
                body = body.encode()


            asgi_cycle = HTTPCycle(
                scope, body=body, text_mime_types=self.text_mime_types, use_multi_value_headers=use_multi_value_headers
            )
            response = asgi_cycle(self.app)

            return response
