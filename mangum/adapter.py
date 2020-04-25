import base64
import asyncio
import urllib.parse
import typing
import os
from dataclasses import dataclass

from mangum.lifespan import Lifespan
from mangum.utils import get_logger
from mangum.types import ASGIApp
from mangum.protocols.http import HTTPCycle
from mangum.protocols.websockets import WebSocketCycle
from mangum.connections import WebSocket, WebSocketError, __ERR__


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


@dataclass
class Mangum:

    app: ASGIApp
    enable_lifespan: bool = True
    api_gateway_base_path: typing.Optional[str] = None
    text_mime_types: typing.Optional[typing.List[str]] = None
    log_level: str = "info"

    def __post_init__(self) -> None:
        self.logger = get_logger("mangum", log_level=self.log_level)
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
        if is_http_api:
            source_ip = event["requestContext"]["http"]["sourceIp"]
            query_string = event.get("rawQueryString")
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
        if __ERR__:  # pragma: no cover
            raise ImportError(__ERR__)

        event_type = event["requestContext"]["eventType"]
        connection_id = event["requestContext"]["connectionId"]
        response = {"statusCode": 200}

        self.logger.debug("Received WebSocket event: %s", event_type)

        if event_type == "CONNECT":

            # The initial connect event. Parse and store the scope for the connection
            # in DynamoDB to be retrieved in subsequent message events for this request.
            headers = (
                {k.lower(): v for k, v in event.get("headers").items()}  # type: ignore
                if event.get("headers")
                else {}
            )
            server = get_server(headers)
            source_ip = event["requestContext"].get("identity", {}).get("sourceIp")
            client = (source_ip, 0)

            # root_path = event["requestContext"]["stage"]

            initial_scope = {
                "type": "websocket",
                "path": "/ws",
                "headers": headers,  # The headers must be JSON serializable.
                "raw_path": None,
                "root_path": "",
                "scheme": headers.get("x-forwarded-proto", "wss"),
                "query_string": "",
                "server": server,
                "client": client,
                "aws": {"event": event, "context": None},
            }

            try:
                websocket = WebSocket(connection_id)
                websocket.accept(initial_scope)
            except WebSocketError as exc:
                self.logger.error(exc)
                response = {"statusCode": 500}

        elif event_type == "MESSAGE":
            stage = event["requestContext"]["stage"]
            domain_name = event["requestContext"]["domainName"]
            endpoint_url = os.environ.get(
                "APIGW_ENDPOINT_URL", f"http://{domain_name}/{stage}"
            )
            try:
                websocket = WebSocket(connection_id, endpoint_url=endpoint_url)
                websocket.connect()
            except WebSocketError as exc:
                self.logger.error(exc)
                response = {"statusCode": 500}
            else:
                asgi_cycle = WebSocketCycle(websocket, self.log_level)
                asgi_cycle.put_message({"type": "websocket.connect"})
                asgi_cycle.put_message(
                    {
                        "type": "websocket.receive",
                        "path": "/",
                        "bytes": None,
                        "text": event["body"],
                    }
                )
                asgi_cycle.put_message({"type": "websocket.disconnect", "code": 1001})
                response = asgi_cycle(self.app)

        elif event_type == "DISCONNECT":
            websocket = WebSocket(connection_id)
            websocket.disconnect()

        return response
