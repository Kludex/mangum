import base64
import asyncio
import traceback
import urllib.parse
import typing
import json
from dataclasses import dataclass

from mangum.lifespan import Lifespan
from mangum.utils import get_logger, make_response, get_connections
from mangum.types import ASGIScope, ASGIApp, AWSEvent, AWSContext, AWSResponse
from mangum.asgi import ASGIHTTPCycle, ASGIWebSocketCycle
from mangum.exceptions import ASGIWebSocketCycleException


@dataclass
class Mangum:

    app: ASGIApp
    debug: bool = False
    enable_lifespan: bool = True

    def __post_init__(self) -> None:
        self.logger = get_logger()

        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            self.lifespan = Lifespan(self.app, logger=self.logger)
            loop.create_task(self.lifespan.run())
            loop.run_until_complete(self.lifespan.wait_startup())

    def __call__(self, event: AWSEvent, context: AWSContext) -> AWSResponse:
        try:
            response = self.handler(event, context)
        except Exception as exc:
            if self.debug:
                content = traceback.format_exc()
                return make_response(content, status_code=500)
            raise exc
        else:
            return response

    def get_scope_from_db(
        self, connection_id: str, connections: typing.Any
    ) -> ASGIScope:
        scope_json = connections.get_item(Key={"connectionId": connection_id})["Item"][
            "scope"
        ]
        scope = json.loads(scope_json)
        query_string = scope["query_string"]
        headers = scope["headers"]
        headers = [[k.encode(), v.encode()] for k, v in headers.items()]
        query_string = query_string.encode()
        scope.update({"headers": headers, "query_string": query_string})
        return scope

    def handle_http(self, event: AWSEvent, context: AWSContext) -> AWSResponse:
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

    def handle_ws(self, event: AWSEvent, context: AWSContext) -> AWSResponse:
        request_context = event["requestContext"]
        connection_id = request_context.get("connectionId")
        domain_name = request_context.get("domainName")
        stage = request_context.get("stage")
        event_type = request_context["eventType"]
        endpoint_url = f"https://{domain_name}/{stage}"

        if event_type == "CONNECT":
            headers = event["headers"]
            client_addr = (
                event["requestContext"].get("identity", {}).get("sourceIp", None)
            )
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
            connections = get_connections()
            result = connections.put_item(
                Item={"connectionId": connection_id, "scope": json.dumps(scope)}
            )
            status_code = result.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code != 200:
                # error creating connection in db
                return make_response("Error.", status_code=500)
            return make_response("OK", status_code=200)

        elif event_type == "MESSAGE":
            event_body = json.loads(event["body"])
            event_data = event_body["data"] or b""
            connections = get_connections()
            scope = self.get_scope_from_db(
                connection_id=connection_id, connections=connections
            )
            asgi_cycle = ASGIWebSocketCycle(
                scope,
                endpoint_url=endpoint_url,
                connection_id=connection_id,
                connections=connections,
            )
            message = {
                "type": "websocket.receive",
                "path": "/ws",
                "bytes": None,
                "text": None,
            }
            if isinstance(event_data, bytes):
                message["bytes"] = event_data
            elif isinstance(event_data, str):
                message["text"] = event_data

            asgi_cycle.put_message({"type": "websocket.connect"})
            asgi_cycle.put_message(message)

            try:
                asgi_cycle(self.app)
            except ASGIWebSocketCycleException as exc:
                return make_response("Error", status_code=500)

            return make_response("OK", status_code=200)

        elif event_type == "DISCONNECT":
            connections = get_connections()
            result = connections.delete_item(Key={"connectionId": connection_id})
            status_code = result.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code != 200:
                return make_response("WebSocket disconnect error.", status_code=500)

            return make_response("OK", status_code=200)

    def handler(self, event: dict, context: dict) -> dict:
        if "httpMethod" in event:
            response = self.handle_http(event, context)
        else:
            response = self.handle_ws(event, context)

        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.lifespan.wait_shutdown())

        return response
