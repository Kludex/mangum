import base64
import asyncio
import urllib.parse
import json
import typing
from dataclasses import dataclass

from mangum.lifespan import Lifespan
from mangum.utils import get_logger, make_response
from mangum.types import ASGIApp
from mangum.protocols.http import ASGIHTTPCycle
from mangum.protocols.websockets import ASGIWebSocketCycle
from mangum.exceptions import ASGIWebSocketCycleException
from mangum.connections import ConnectionTable, __ERR__

TEXT_MIME_TYPES = ("text/.*", r".*\bjson", r".*\bxml")


def get_server_and_client(
    event: dict, is_http_api: bool = False
) -> typing.Tuple:  # pragma: no cover
    """
    Parse the server and client for the scope definition, if possible.
    """

    if is_http_api:
        client_addr = event["requestContext"]["http"]["sourceIp"]
    else:
        client_addr = event["requestContext"].get("identity", {}).get("sourceIp", None)

    client = (client_addr, 0)

    headers = event.get("headers") or {}
    server_addr = headers.get("host") if is_http_api else headers.get("Host")

    if server_addr is not None:
        if ":" not in server_addr:
            server_port = 80
        else:
            server_addr, server_port = server_addr.split(":")
            server_port = int(server_port)

        server = (server_addr, server_port)  # type: typing.Any
    else:
        server = None

    return server, client


@dataclass
class Mangum:

    app: ASGIApp
    enable_lifespan: bool = True
    api_gateway_base_path: typing.Optional[str] = None
    text_mime_types: typing.Tuple[str, ...] = TEXT_MIME_TYPES
    log_level: str = "info"

    def __post_init__(self) -> None:
        self.logger = get_logger(log_level=self.log_level)
        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            self.lifespan = Lifespan(self.app, logger=self.logger)
            loop.create_task(self.lifespan.run())
            loop.run_until_complete(self.lifespan.wait_startup())

    def __call__(self, event: dict, context: dict) -> dict:
        try:
            response = self.handler(event, context)
        except BaseException as exc:
            raise exc
        return response

    def strip_base_path(self, path: str) -> str:
        if self.api_gateway_base_path:
            script_name = "/" + self.api_gateway_base_path
            if path.startswith(script_name):
                path = path[len(script_name) :]
        return urllib.parse.unquote(path or "/")

    def handler(self, event: dict, context: dict) -> dict:

        if "eventType" not in event["requestContext"]:
            response = self.handle_http(event, context)
        else:

            response = self.handle_ws(event, context)

        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.lifespan.wait_shutdown())

        return response

    def handle_http(self, event: dict, context: dict) -> dict:
        is_http_api = "http" in event["requestContext"]
        server, client = get_server_and_client(event, is_http_api)
        headers = event.get("headers") or {}
        headers_key_value_pairs = [
            [k.lower().encode(), v.encode()] for k, v in headers.items()
        ]

        if is_http_api:
            query_string = event.get("rawQueryString")
        else:
            multi_value_query_string_params = event["multiValueQueryStringParameters"]
            query_string = (
                urllib.parse.urlencode(
                    multi_value_query_string_params, doseq=True
                ).encode()
                if multi_value_query_string_params
                else b""
            )

        event_path = (
            event["requestContext"]["http"]["path"] if is_http_api else event["path"]
        )
        http_method = (
            event["requestContext"]["http"]["method"]
            if is_http_api
            else event["httpMethod"]
        )

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": http_method,
            "headers": headers_key_value_pairs,
            "path": self.strip_base_path(event_path),
            "raw_path": None,
            "root_path": "",
            "scheme": headers.get("X-Forwarded-Proto", "https"),
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

        asgi_cycle = ASGIHTTPCycle(
            scope, text_mime_types=self.text_mime_types, logger=self.logger
        )
        asgi_cycle.put_message(
            {"type": "http.request", "body": body, "more_body": False}
        )
        response = asgi_cycle(self.app)
        return response

    def handle_ws(self, event: dict, context: dict) -> dict:
        if __ERR__:  # pragma: no cover
            raise ImportError(__ERR__)

        request_context = event["requestContext"]
        connection_id = request_context.get("connectionId")
        domain_name = request_context.get("domainName")
        stage = request_context.get("stage")
        event_type = request_context["eventType"]
        endpoint_url = f"https://{domain_name}/{stage}"

        if event_type == "CONNECT":
            # The initial connect event. Parse and store the scope for the connection
            # in DynamoDB to be retrieved in subsequent message events for this request.
            server, client = get_server_and_client(event)

            # The scope headers must be JSON serializable to store in DynamoDB, but
            # they will be parsed on the MESSAGE event.
            headers = event.get("headers") or {}

            root_path = event["requestContext"]["stage"]
            scope = {
                "type": "websocket",
                "path": "/",
                "headers": headers,
                "raw_path": None,
                "root_path": root_path,
                "scheme": headers.get("X-Forwarded-Proto", "wss"),
                "query_string": "",
                "server": server,
                "client": client,
                "aws": {"event": event, "context": context},
            }
            connection_table = ConnectionTable()
            status_code = connection_table.update_item(
                connection_id, scope=json.dumps(scope)
            )

            if status_code != 200:  # pragma: no cover
                return make_response("Error", status_code=500)
            return make_response("OK", status_code=200)

        elif event_type == "MESSAGE":

            connection_table = ConnectionTable()
            item = connection_table.get_item(connection_id)
            if not item:  # pragma: no cover
                return make_response("Error", status_code=500)

            # Retrieve and deserialize the scope entry created in the connect event for
            # the current connection.
            scope = json.loads(item["scope"])

            # Ensure the scope definition complies with the ASGI spec.
            query_string = scope["query_string"]
            headers = scope["headers"]
            headers = [[k.encode(), v.encode()] for k, v in headers.items()]  # type: ignore
            query_string = query_string.encode()  # type: ignore
            scope.update({"headers": headers, "query_string": query_string})

            asgi_cycle = ASGIWebSocketCycle(
                scope,
                endpoint_url=endpoint_url,
                connection_id=connection_id,
                connection_table=connection_table,
            )
            asgi_cycle.app_queue.put_nowait({"type": "websocket.connect"})
            asgi_cycle.app_queue.put_nowait(
                {
                    "type": "websocket.receive",
                    "path": "/",
                    "bytes": None,
                    "text": event["body"],
                }
            )

            try:
                asgi_cycle(self.app)
            except ASGIWebSocketCycleException:  # pragma: no cover
                return make_response("Error", status_code=500)
            return make_response("OK", status_code=200)

        elif event_type == "DISCONNECT":
            connection_table = ConnectionTable()
            status_code = connection_table.delete_item(connection_id)
            if status_code != 200:  # pragma: no cover
                return make_response("WebSocket disconnect error.", status_code=500)
            return make_response("OK", status_code=200)
        return make_response("Error", status_code=500)  # pragma: no cover
