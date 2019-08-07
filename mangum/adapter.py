import base64
import asyncio
import traceback
import urllib.parse
import typing
import json
import logging
from dataclasses import dataclass

from mangum.lifespan import Lifespan
from mangum.utils import get_logger, make_response
from mangum.types import ASGIApp
from mangum.asgi import ASGIHTTPCycle, ASGIWebSocketCycle
from mangum.exceptions import ASGIWebSocketCycleException
from mangum.connections import ConnectionTable


@dataclass
class Mangum:

    app: ASGIApp
    debug: bool = False
    enable_lifespan: bool = True
    logger: logging.Logger = get_logger()

    def __post_init__(self) -> None:
        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            self.lifespan = Lifespan(self.app, logger=self.logger)
            loop.create_task(self.lifespan.run())
            loop.run_until_complete(self.lifespan.wait_startup())

    def __call__(
        self, event: typing.Dict[str, str], context: typing.Dict[str, str]
    ) -> typing.Dict[str, str]:
        try:
            response = self.handler(event, context)
        except Exception as exc:
            if self.debug:
                content = traceback.format_exc()
                return make_response(content, status_code=500)
            raise exc
        else:
            return response

    def get_server_and_client(
        self, event: typing.Dict[str, str]
    ) -> typing.Tuple:  # pragma: no cover
        """
        Parse the server and client keys for the scope definition, if possible.
        """
        client_addr = event["requestContext"].get("identity", {}).get("sourceIp", None)
        client = (client_addr, 0)
        server_addr = event["headers"].get("Host", None)
        if server_addr is not None:
            if ":" not in server_addr:
                server_port = 80
            else:
                server_port = int(server_addr.split(":")[1])

            server = (server_addr, server_port)
        else:
            server = None
        return server, client

    def handle_http(
        self, event: typing.Dict[str, str], context: typing.Dict[str, str]
    ) -> typing.Dict[str, str]:
        server, client = self.get_server_and_client(event)
        headers = [
            [k.lower().encode(), v.encode()] for k, v in event["headers"].items()
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
            "headers": headers,
            "path": urllib.parse.unquote(event["path"]),
            "raw_path": None,
            "root_path": event["requestContext"]["stage"],
            "scheme": event["headers"].get("X-Forwarded-Proto", "https"),
            "query_string": query_string,
            "server": server,
            "client": client,
        }
        binary = event.get("isBase64Encoded", False)
        body = event["body"] or b""
        if binary:
            body = base64.b64decode(body)
        elif not isinstance(body, bytes):
            body = body.encode()
        asgi_cycle = ASGIHTTPCycle(scope, binary=binary)
        asgi_cycle.put_message(
            {"type": "http.request", "body": body, "more_body": False}
        )
        response = asgi_cycle(self.app)
        return response

    def handle_ws(
        self, event: typing.Dict[str, str], context: typing.Dict[str, str]
    ) -> typing.Dict[str, str]:
        request_context = event["requestContext"]
        connection_id = request_context.get("connectionId")
        domain_name = request_context.get("domainName")
        stage = request_context.get("stage")
        event_type = request_context["eventType"]
        endpoint_url = f"https://{domain_name}/{stage}"

        if event_type == "CONNECT":
            server, client = self.get_server_and_client(event)
            headers = event["headers"]
            root_path = event["requestContext"]["stage"]
            scope = {
                "type": "websocket",
                "path": "/ws",
                "headers": headers,
                "raw_path": None,
                "root_path": root_path,
                "scheme": event["headers"].get("X-Forwarded-Proto", "wss"),
                "query_string": "",
                "server": server,
                "client": client,
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
            asgi_cycle.put_message({"type": "websocket.connect"})
            asgi_cycle.put_message(
                {
                    "type": "websocket.receive",
                    "path": "/ws",
                    "bytes": None,
                    "text": event_data,
                }
            )
            try:
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

    def handler(
        self, event: typing.Dict[str, str], context: typing.Dict[str, str]
    ) -> typing.Dict[str, str]:
        if "httpMethod" in event:
            response = self.handle_http(event, context)
        else:
            response = self.handle_ws(event, context)
        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.lifespan.wait_shutdown())
        return response
