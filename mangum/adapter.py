import asyncio
import base64
import urllib.parse
import typing
import logging
import os
import warnings
from contextlib import ExitStack
from dataclasses import dataclass

from mangum.types import ASGIApp
from mangum.exceptions import ConfigurationError
from mangum.protocols.lifespan import LifespanCycle
from mangum.protocols.http import HTTPCycle
from mangum.protocols.websockets import WebSocketCycle
from mangum.backends import WebSocket


DEFAULT_TEXT_MIME_TYPES = [
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
]


def get_server(headers: dict) -> typing.Tuple:  # pragma: no cover
    """
    Parse the host and port from the event headers to use as the `server` key in the
    ASGI connection scope.
    """
    server_name = headers.get("host", "mangum")
    if ":" not in server_name:
        server_port = headers.get("x-forwarded-port", 80)
    else:
        server_name, server_port = server_name.split(":")
    server = (server_name, int(server_port))

    return server


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


@dataclass
class Mangum:
    """
    Creates an adapter instance.

    **Parameters:**

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
    lifespan: str = "auto"
    log_level: str = "info"
    api_gateway_base_path: typing.Optional[str] = None
    text_mime_types: typing.Optional[typing.List[str]] = None
    dsn: typing.Optional[str] = None
    api_gateway_endpoint_url: typing.Optional[str] = None
    api_gateway_region_name: typing.Optional[str] = None
    enable_lifespan: bool = True  # Deprecated.

    def __post_init__(self) -> None:
        self.logger = get_logger(self.log_level)
        if not self.enable_lifespan:  # pragma: no cover
            warnings.warn(
                "The `enable_lifespan` parameter will be removed in a future release. "
                "It is replaced by `lifespan` setting.",
                DeprecationWarning,
                stacklevel=2,
            )
        if self.lifespan not in ("auto", "on", "off"):  # pragma: no cover
            raise ConfigurationError(
                "Invalid argument supplied for `lifespan`. Choices are: auto|on|off."
            )

    def __call__(self, event: dict, context: dict) -> dict:
        return self.handler(event, context)

    def strip_base_path(self, path: str) -> str:
        if self.api_gateway_base_path:
            script_name = "/" + self.api_gateway_base_path
            if path.startswith(script_name):
                path = path[len(script_name) :]

        return urllib.parse.unquote(path or "/")

    def handler(self, event: dict, context: dict) -> dict:
        with ExitStack() as stack:

            # Ignore lifespan events entirely if the `lifespan` setting is `off`.
            if self.lifespan in ("auto", "on"):
                asgi_cycle: typing.ContextManager = LifespanCycle(
                    self.app, self.lifespan
                )
                stack.enter_context(asgi_cycle)

            if "eventType" in event["requestContext"]:
                response = self.handle_ws(event, context)
            else:
                is_http_api = "http" in event["requestContext"]
                response = self.handle_http(event, context, is_http_api=is_http_api)

        return response

    def handle_http(self, event: dict, context: dict, *, is_http_api: bool) -> dict:
        self.logger.info("HTTP event received.")
        if is_http_api:
            source_ip = event["requestContext"]["http"]["sourceIp"]
            query_string = event.get("rawQueryString", "").encode()
            path = event["requestContext"]["http"]["path"]
            http_method = event["requestContext"]["http"]["method"]
        else:
            source_ip = event["requestContext"].get("identity", {}).get("sourceIp")
            multi_value_query_string_params = event["multiValueQueryStringParameters"]
            query_string = (
                urllib.parse.urlencode(
                    multi_value_query_string_params, doseq=True
                ).encode()
                if multi_value_query_string_params
                else b""
            )
            path = event["path"]
            http_method = event["httpMethod"]

        headers = (
            {k.lower(): v for k, v in event.get("headers").items()}  # type: ignore
            if event.get("headers")
            else {}
        )
        server = get_server(headers)
        client = (source_ip, 0)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": http_method,
            "headers": [[k.encode(), v.encode()] for k, v in headers.items()],
            "path": self.strip_base_path(path),
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

        if self.text_mime_types:
            text_mime_types = self.text_mime_types + DEFAULT_TEXT_MIME_TYPES
        else:
            text_mime_types = DEFAULT_TEXT_MIME_TYPES

        asgi_cycle = HTTPCycle(scope, body=body, text_mime_types=text_mime_types)
        response = asgi_cycle(self.app)

        return response

    def handle_ws(self, event: dict, context: dict) -> dict:
        if self.dsn is None:
            raise ConfigurationError(
                "A `dsn` connection string is required for WebSocket support."
            )
        request_context = event["requestContext"]
        event_type = request_context["eventType"]
        connection_id = request_context["connectionId"]
        self.logger.debug(
            "%s event received for WebSocket connection %s", event_type, connection_id
        )
        api_gateway_endpoint_url = (
            self.api_gateway_endpoint_url
            or f"https://{request_context['domainName']}/{request_context['stage']}"
        )
        api_gateway_region_name = (
            self.api_gateway_region_name or os.environ["AWS_REGION"]
        )

        websocket = WebSocket(
            connection_id,
            dsn=self.dsn,
            api_gateway_endpoint_url=api_gateway_endpoint_url,
            api_gateway_region_name=api_gateway_region_name,
        )

        if event_type == "CONNECT":
            headers = (
                {k.lower(): v for k, v in event.get("headers").items()}  # type: ignore
                if event.get("headers")
                else {}
            )
            server = get_server(headers)
            source_ip = event["requestContext"].get("identity", {}).get("sourceIp")
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
                "aws.events": [event],
                "extensions": {"websocket.broadcast": {"subscriptions": []}},
            }
            asyncio.run(websocket.on_connect(initial_scope))
            response = {"statusCode": 200}

        elif event_type == "DISCONNECT":
            asyncio.run(websocket.on_disconnect())
            response = {"statusCode": 200}

        elif event_type == "MESSAGE":
            body = event.get("body", "")
            asgi_cycle = WebSocketCycle(body, websocket=websocket)
            response = asyncio.run(asgi_cycle(self.app, event=event))

        return response
