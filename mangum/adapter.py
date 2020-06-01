import base64
import typing
import os
import warnings
from dataclasses import dataclass
from contextlib import ExitStack

from mangum.types import ASGIApp
from mangum.protocols.lifespan import LifespanCycle
from mangum.protocols.http import HTTPCycle
from mangum.protocols.websockets import WebSocketCycle
from mangum.websocket import WebSocket
from mangum.config import Config
from mangum.exceptions import ConfigurationError


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
    lifespan: str = "auto"
    log_level: str = "info"
    api_gateway_base_path: typing.Optional[str] = None
    text_mime_types: typing.Optional[typing.List[str]] = None
    dsn: typing.Optional[str] = None
    api_gateway_endpoint_url: typing.Optional[str] = None
    api_gateway_region_name: typing.Optional[str] = None
    enable_lifespan: bool = True  # Deprecated.

    def __post_init__(self) -> None:
        if not self.enable_lifespan:  # pragma: no cover
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
        self.config: Config = Config(
            self.lifespan,
            self.log_level,
            self.api_gateway_base_path,
            self.text_mime_types,
            self.dsn,
            self.api_gateway_endpoint_url,
            self.api_gateway_region_name,
        )

    def __call__(self, event: dict, context: dict) -> dict:
        with ExitStack() as stack:

            # Ignore lifespan events entirely if the `lifespan` setting is `off`.
            if self.config.lifespan in ("auto", "on"):
                asgi_cycle: typing.ContextManager = LifespanCycle(
                    self.app, self.config.lifespan
                )
                stack.enter_context(asgi_cycle)

            if "eventType" in event["requestContext"]:
                response = self.handle_ws(event, context)
            else:
                response = self.handle_http(event, context)

        return response

    def handle_http(self, event: dict, context: dict) -> dict:
        self.config.logger.info("HTTP event received.")

        scope = self.config.make_http_scope(event, context)
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

    def handle_ws(self, event: dict, context: dict) -> dict:
        self.config.logger.info("WebSocket event received.")

        if self.config.dsn is None:
            raise ConfigurationError(
                "A `dsn` connection string is required for WebSocket support."
            )

        request_context = event["requestContext"]
        event_type = request_context["eventType"]
        connection_id = request_context["connectionId"]
        stage = request_context["stage"]
        domain_name = request_context["domainName"]
        api_gateway_endpoint_url = (
            self.config.api_gateway_endpoint_url or f"https://{domain_name}/{stage}"
        )
        api_gateway_region_name = (
            self.config.api_gateway_region_name or os.environ["AWS_REGION"]
        )
        websocket = WebSocket(
            connection_id,
            dsn=self.config.dsn,
            api_gateway_endpoint_url=api_gateway_endpoint_url,
            api_gateway_region_name=api_gateway_region_name,
        )

        if event_type == "CONNECT":
            scope = self.config.make_websocket_scope(event)
            websocket.create(scope)
            response = {"statusCode": 200}

        elif event_type == "MESSAGE":
            websocket.fetch()
            asgi_cycle = WebSocketCycle(event.get("body", ""), websocket=websocket)
            response = asgi_cycle(self.app)

        elif event_type == "DISCONNECT":
            websocket.delete()
            response = {"statusCode": 200}

        return response
