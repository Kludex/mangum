import asyncio
import base64
import typing
import urllib.parse

import warnings
from dataclasses import dataclass, InitVar
from contextlib import ExitStack

from mangum.types import ASGIApp
from mangum.protocols.lifespan import LifespanCycle
from mangum.protocols.http import HTTPCycle
from mangum.protocols.websockets import WebSocketCycle
from mangum.backends import WebSocket
from mangum.config import Config
from mangum.exceptions import ConfigurationError


def get_server_and_headers(event: dict) -> typing.Tuple:  # pragma: no cover
    headers = (
        {k.lower(): v for k, v in event.get("headers").items()}  # type: ignore
        if event.get("headers")
        else {}
    )

    server_name = headers.get("host", "mangum")
    if ":" not in server_name:
        server_port = headers.get("x-forwarded-port", 80)
    else:
        server_name, server_port = server_name.split(":")
    server = (server_name, int(server_port))

    return server, headers


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
    * **dsn** - A connection string required to configure a supported WebSocket backend.
    * **api_gateway_endpoint_url** - A string endpoint url to use for API Gateway when
    sending data to WebSocket connections. Default is `None`.
    * **api_gateway_region_name** - A string region name to use for API Gateway when
    sending data to WebSocket connections. Default is `AWS_REGION` environment variable.
    """

    app: ASGIApp
    lifespan: InitVar[str] = "auto"
    log_level: InitVar[str] = "info"
    api_gateway_base_path: InitVar[typing.Optional[str]] = None
    text_mime_types: InitVar[typing.Optional[typing.List[str]]] = None
    dsn: InitVar[typing.Optional[str]] = None
    api_gateway_endpoint_url: InitVar[typing.Optional[str]] = None
    api_gateway_region_name: InitVar[typing.Optional[str]] = None
    broadcast: InitVar[bool] = False
    enable_lifespan: InitVar[bool] = True  # Deprecated.

    def __post_init__(
        self,
        lifespan: str,
        log_level: str,
        api_gateway_base_path: str,
        text_mime_types: str,
        dsn: str,
        api_gateway_endpoint_url: str,
        api_gateway_region_name: str,
        broadcast: bool,
        enable_lifespan: bool,
    ) -> None:
        if not enable_lifespan:  # pragma: no cover
            warnings.warn(
                "The `enable_lifespan` parameter will be removed in a future release. "
                "It is replaced by `lifespan` setting.",
                DeprecationWarning,
                stacklevel=2,
            )
        if lifespan not in ("auto", "on", "off"):  # pragma: no cover
            raise ConfigurationError(
                "Invalid argument supplied for `lifespan`. Choices are: auto|on|off"
            )
        if log_level not in ("critical", "error", "warning", "info", "debug"):
            raise ConfigurationError(  # pragma: no cover
                "Invalid argument supplied for `log_level`. "
                "Choices are: critical|error|warning|info|debug"
            )
        self.config: Config = Config(
            lifespan,
            log_level,
            api_gateway_base_path,
            text_mime_types,
            dsn,
            api_gateway_endpoint_url,
            api_gateway_region_name,
            broadcast,
        )

    def __call__(self, event: dict, context: dict) -> dict:
        request_context = event["requestContext"]
        self.config.update(request_context)

        with ExitStack() as stack:
            if self.config.lifespan != "off":
                asgi_cycle: typing.ContextManager = LifespanCycle(
                    self.app, self.config.lifespan
                )
                stack.enter_context(asgi_cycle)

            if self.config.api_gateway_event_type in ("HTTP", "REST"):
                self.config.logger.debug("HTTP event received.")
                if self.config.api_gateway_event_type == "HTTP":
                    source_ip = request_context["http"]["sourceIp"]
                    path = request_context["http"]["path"]
                    http_method = request_context["http"]["method"]
                    query_string = event.get("rawQueryString", "").encode()
                else:
                    source_ip = request_context.get("identity", {}).get("sourceIp")
                    multi_value_query_string_params = event[
                        "multiValueQueryStringParameters"
                    ]
                    query_string = (
                        urllib.parse.urlencode(
                            multi_value_query_string_params, doseq=True
                        ).encode()
                        if multi_value_query_string_params
                        else b""
                    )
                    path = event["path"]
                    http_method = event["httpMethod"]

                server, headers = get_server_and_headers(event)
                client = (source_ip, 0)

                if not path:  # pragma: no cover
                    path = "/"
                elif self.config.api_gateway_base_path:
                    if path.startswith(self.config.api_gateway_base_path):
                        path = path[len(self.config.api_gateway_base_path) :]

                scope = {
                    "type": "http",
                    "http_version": "1.1",
                    "method": http_method,
                    "headers": [[k.encode(), v.encode()] for k, v in headers.items()],
                    "path": urllib.parse.unquote(path),
                    "raw_path": None,
                    "root_path": "",
                    "scheme": headers.get("x-forwarded-proto", "https"),
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
                    scope,
                    body=body,
                    text_mime_types=self.config.text_mime_types,  # type: ignore
                )
                response = asgi_cycle(self.app)

                return response

            websocket = WebSocket(
                self.config.dsn,
                self.config.connection_id,
                self.config.api_gateway_endpoint_url,
                self.config.api_gateway_region_name,
                self.config.broadcast,
            )

            if self.config.api_gateway_event_type == "CONNECT":
                server, headers = get_server_and_headers(event)
                source_ip = request_context.get("identity", {}).get("sourceIp")
                client = (source_ip, 0)
                initial_scope = {
                    "type": "websocket",
                    "path": "/",
                    "headers": headers,
                    "raw_path": None,
                    "root_path": "",
                    "scheme": headers.get("x-forwarded-proto", "wss"),
                    "query_string": "",
                    "server": server,
                    "client": client,
                    "asgi": {"version": "3.0"},
                    "aws.events": {"connect": event, "message": {}},
                }
                if self.config.broadcast:
                    initial_scope["aws.subscriptions"] = []
                loop = asyncio.get_event_loop()
                loop.run_until_complete(websocket.on_connect(initial_scope))

            elif self.config.api_gateway_event_type == "MESSAGE":
                body = event.get("body", "")
                asgi_cycle = WebSocketCycle(body, websocket=websocket)
                response = asgi_cycle(self.app, request_context=request_context)

                return response

            elif self.config.api_gateway_event_type == "DISCONNECT":
                loop = asyncio.get_event_loop()
                loop.run_until_complete(websocket.on_disconnect())
