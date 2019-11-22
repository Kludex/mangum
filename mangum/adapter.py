import base64
import asyncio
import traceback
import urllib.parse
import typing
import json
import logging
from dataclasses import dataclass

from mangum.lifespan import Lifespan
from mangum.utils import get_logger, get_server_and_client, make_response
from mangum.types import ASGIApp
from mangum.protocols.http import ASGIHTTPCycle
from mangum.protocols.websockets import ASGIWebSocketCycle
from mangum.exceptions import ASGIWebSocketCycleException

from mangum.connections import ConnectionTable, __ERR__


class Mangum:

    enable_lifespan: bool = True
    log_level: str = "info"

    def __init__(
        self, app: ASGIApp, enable_lifespan: bool = True, log_level: str = "info"
    ) -> None:
        # Incompatible types in assignment (expression has type
        #                   "Callable[[Dict[str, Any], Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]"
        # variable has type "Callable[[Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]")
        self.app = app
        self.enable_lifespan = enable_lifespan
        self.log_level = log_level
        self.logger = get_logger(log_level=self.log_level)
        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            # Argument 1 to "Lifespan" has incompatible type
            #          "Callable[[                Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]"
            # expected "Callable[[Dict[str, Any], Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]"
            self.lifespan = Lifespan(self.app, self.logger)
            loop.create_task(self.lifespan.run())
            loop.run_until_complete(self.lifespan.wait_startup())

    def __call__(self, event: dict, context: dict) -> dict:
        try:
            response = self.handler(event, context)
        except BaseException as exc:
            raise exc
        return response

    def handler(self, event: dict, context: dict) -> dict:
        if "httpMethod" in event:
            response = self.handle_http(event, context)
        else:

            response = self.handle_ws(event, context)

        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.lifespan.wait_shutdown())

        return response

    def handle_http(self, event: dict, context: dict) -> dict:
        server, client = get_server_and_client(event)
        headers = event.get("headers", {})
        headers_key_value_pairs = [
            [k.lower().encode(), v.encode()] for k, v in headers.items()
        ]
        query_string_params = event["queryStringParameters"]
        query_string = (
            urllib.parse.urlencode(query_string_params).encode()
            if query_string_params
            else b""
        )
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": event["httpMethod"],
            "headers": headers_key_value_pairs,
            "path": urllib.parse.unquote(event["path"]),
            "raw_path": None,
            "root_path": "",
            "scheme": headers.get("X-Forwarded-Proto", "https"),
            "query_string": query_string,
            "server": server,
            "client": client,
            "asgi": {"version": "3.0"},
            "aws": {"event": event, "context": context},
        }

        is_binary = event.get("isBase64Encoded", False)
        body = event["body"] or b""
        if is_binary:
            body = base64.b64decode(body)
        elif not isinstance(body, bytes):
            body = body.encode()

        asgi_cycle = ASGIHTTPCycle(scope, is_binary=is_binary, logger=self.logger)
        asgi_cycle.put_message(
            {"type": "http.request", "body": body, "more_body": False}
        )
        # Argument 1 to "__call__" of "ASGIHTTPCycle" has incompatible type
        #          "Callable[[                Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]"
        # expected "Callable[[Dict[str, Any], Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]
        response = asgi_cycle(self.app)
        return response

    def handle_ws(self, event: dict, context: dict) -> dict:
        if __ERR__:
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
            headers = event.get("headers", {})
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
                # TODO: Improve error handling
                return make_response("Error", status_code=500)
            return make_response("OK", status_code=200)

        elif event_type == "MESSAGE":
            event_body = json.loads(event["body"])
            event_data = event_body["data"] or ""

            connection_table = ConnectionTable()
            item = connection_table.get_item(connection_id)
            if not item:  # pragma: no cover
                # TODO: Improve error handling
                return make_response("Error", status_code=500)

            # Retrieve and deserialize the scope entry created in the connect event for
            # the current connection.
            scope = json.loads(item["scope"])

            # Ensure the scope definitions comply with the ASGI spec.
            query_string = scope["query_string"]
            headers = scope["headers"]
            headers = [[k.encode(), v.encode()] for k, v in headers.items()]
            query_string = query_string.encode()
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
                    "text": event_data,
                }
            )

            try:
                # Argument 1 to "__call__" of "ASGIWebSocketCycle" has incompatible type
                #          "Callable[[                Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]"
                # expected "Callable[[Dict[str, Any], Callable[[], Awaitable[Dict[str, Any]]], Callable[[Dict[str, Any]], Awaitable[None]]], Awaitable[None]]"
                asgi_cycle(self.app)
            except ASGIWebSocketCycleException:  # pragma: no cover
                # TODO: Improve error handling
                return make_response("Error", status_code=500)
            return make_response("OK", status_code=200)

        elif event_type == "DISCONNECT":
            connection_table = ConnectionTable()
            status_code = connection_table.delete_item(connection_id)
            if status_code != 200:  # pragma: no cover
                # TODO: Improve error handling
                return make_response("WebSocket disconnect error.", status_code=500)
            return make_response("OK", status_code=200)

        return make_response("Error", status_code=500)  # pragma: no cover

