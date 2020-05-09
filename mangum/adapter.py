import base64
import asyncio
import urllib.parse
import typing
import logging
import os
from dataclasses import dataclass

from mangum.lifespan import Lifespan
from mangum.types import ASGIApp
from mangum.protocols.http import HTTPCycle
from mangum.protocols.ws import WebSocketCycle
from mangum.websocket import WebSocket
from mangum.exceptions import ConfigurationError


DEFAULT_TEXT_MIME_TYPES = [
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
]


def get_server(headers: dict) -> typing.Tuple:  # pragma: no cover
    server_name = headers.get("host", "mangum")
    if ":" not in server_name:
        server_port = headers.get("x-forwarded-port", 80)
    else:
        server_name, server_port = server_name.split(":")
    server = (server_name, int(server_port))

    return server


def get_logger(log_level: str) -> logging.Logger:
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

    app: ASGIApp
    enable_lifespan: bool = True
    log_level: str = "info"
    api_gateway_base_path: typing.Optional[str] = None
    text_mime_types: typing.Optional[typing.List[str]] = None
    dsn: typing.Optional[str] = None
    api_gateway_endpoint_url: typing.Optional[str] = None
    api_gateway_region_name: typing.Optional[str] = None

    def __post_init__(self) -> None:
        self.logger = get_logger(self.log_level)
        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            self.lifespan = Lifespan(self.app)
            loop.create_task(self.lifespan.run())
            loop.run_until_complete(self.lifespan.startup())

    def __call__(self, event: dict, context: dict) -> dict:
        response = self.handler(event, context)

        return response

    def strip_base_path(self, path: str) -> str:
        if self.api_gateway_base_path:
            script_name = "/" + self.api_gateway_base_path
            if path.startswith(script_name):
                path = path[len(script_name) :]

        return urllib.parse.unquote(path or "/")

    def handler(self, event: dict, context: dict) -> dict:
        if "eventType" in event["requestContext"]:
            response = self.handle_ws(event, context)
        else:
            is_http_api = "http" in event["requestContext"]
            response = self.handle_http(event, context, is_http_api=is_http_api)

        if self.enable_lifespan:
            if self.lifespan.is_supported:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.lifespan.shutdown())

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

        asgi_cycle = HTTPCycle(
            scope, text_mime_types=text_mime_types, log_level=self.log_level
        )
        asgi_cycle.put_message(
            {"type": "http.request", "body": body, "more_body": False}
        )
        response = asgi_cycle(self.app)

        return response

    def handle_ws(self, event: dict, context: dict) -> dict:
        if self.dsn is None:
            raise ConfigurationError(
                "A `dsn` connection string is required for WebSocket support."
            )

        event_type = event["requestContext"]["eventType"]
        connection_id = event["requestContext"]["connectionId"]
        stage = event["requestContext"]["stage"]
        domain_name = event["requestContext"]["domainName"]
        self.logger.info(
            "%s event received for WebSocket connection %s", event_type, connection_id
        )

        api_gateway_endpoint_url = (
            self.api_gateway_endpoint_url or f"https://{domain_name}/{stage}"
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
                "aws": {"event": event, "context": None},
            }

            websocket.create(initial_scope)
            response = {"statusCode": 200}

        elif event_type == "MESSAGE":
            websocket.fetch()
            asgi_cycle = WebSocketCycle(websocket, log_level=self.log_level)
            asgi_cycle.put_message({"type": "websocket.connect"})
            asgi_cycle.put_message(
                {"type": "websocket.receive", "bytes": None, "text": event["body"]}
            )

            response = asgi_cycle(self.app)

        elif event_type == "DISCONNECT":
            websocket.delete()
            response = {"statusCode": 200}

        return response
