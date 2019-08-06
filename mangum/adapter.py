import base64
import asyncio
import enum
import os
import traceback
import urllib.parse
import typing
import json
from dataclasses import dataclass, field

import boto3
import botocore

from mangum.lifespan import Lifespan
from mangum.utils import get_logger
from mangum.types import (
    ASGIScope,
    ASGIMessage,
    ASGIApp,
    AWSEvent,
    AWSContext,
    AWSResponse,
)


def make_response(content: str, status_code: int = 500):
    return {
        "statusCode": status_code,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": content,
    }


def get_connections():
    db = boto3.resource("dynamodb")
    connections = db.Table(os.environ["TABLE_NAME"])
    return connections


def send_to_connections(*, data, connections, items, endpoint_url):
    apigw_management = boto3.client(
        "apigatewaymanagementapi", endpoint_url=endpoint_url
    )
    for item in items:
        try:
            apigw_management.post_to_connection(
                ConnectionId=item["connectionId"], Data=data
            )
        except botocore.exceptions.ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 410:
                connections.delete_item(Key={"connectionId": item["connectionId"]})
            else:
                return make_response("Connection error", status_code=500)
    return make_response("OK", status_code=200)


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class ASGICycle:

    scope: ASGIScope
    state: ASGICycleState = ASGICycleState.REQUEST
    binary: bool = False
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.app_queue = asyncio.Queue(loop=self.loop)

    def __call__(self, app: ASGIApp):
        asgi_instance = app(self.scope, self.receive, self.send)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)
        return self.response

    async def receive(self) -> dict:
        message = await self.app_queue.get()
        return message

    def put_message(self, message: ASGIMessage) -> None:
        self.app_queue.put_nowait(message)


@dataclass
class ASGIHTTPCycle(ASGICycle):

    body: bytes = b""

    async def send(self, message: ASGIMessage) -> None:
        if self.state is ASGICycleState.REQUEST:
            if message["type"] != "http.response.start":
                raise RuntimeError(
                    f"Expected 'http.response.start', received: {message['type']}"
                )

            status_code = message["status"]
            headers = {k: v for k, v in message.get("headers", [])}
            self.response["statusCode"] = status_code
            self.response["isBase64Encoded"] = self.binary
            self.response["headers"] = {
                k.decode(): v.decode() for k, v in headers.items()
            }
            self.state = ASGICycleState.RESPONSE

        elif self.state is ASGICycleState.RESPONSE:
            if message["type"] != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message['type']}"
                )

            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            # The body must be completely read before returning the response.
            self.body += body

            if not more_body:
                body = self.body
                if self.binary:
                    body = base64.b64encode(body)
                self.response["body"] = body.decode()
                self.put_message({"type": "http.disconnect"})


@dataclass
class ASGIWebSocketCycle(ASGICycle):

    endpoint_url: str = None

    async def send(self, message: ASGIMessage) -> None:
        if self.state is not ASGICycleState.REQUEST:
            if message["type"] in ("websocket.accept", "websocket.close"):
                self.response["statusCode"] = 200
                self.response["headers"] = {"content-type": "text/plain; charset=utf-8"}
                self.response["body"] = "OK"
                self.state = ASGICycleState.RESPONSE
            else:
                raise RuntimeError(
                    f"Expected 'websocket.accept' or 'websocket.close', received: {message['type']}"
                )
        else:
            bytes_data = message.get("bytes")
            text_data = message.get("text")
            data = text_data if bytes_data is None else bytes_data
            if message["type"] == "websocket.send":
                connections = get_connections()
                items = connections.scan(ProjectionExpression="connectionId").get(
                    "Items"
                )
                if items is None:
                    self.response["statusCode"] = 500
                    self.response["headers"] = {
                        "content-type": "text/plain; charset=utf-8"
                    }
                    self.response["body"] = "Connection error"
                else:
                    self.response = send_to_connections(
                        data=data,
                        connections=connections,
                        items=items,
                        endpoint_url=self.endpoint_url,
                    )

                    # apigw_management = boto3.client(
                    #     "apigatewaymanagementapi", endpoint_url=self.endpoint_url
                    # )
                    # for item in items:
                    #     try:
                    #         apigw_management.post_to_connection(
                    #             ConnectionId=item["connectionId"], Data=data
                    #         )
                    #     except botocore.exceptions.ClientError as exc:
                    #         status_code = exc.response.get("ResponseMetadata", {}).get(
                    #             "HTTPStatusCode"
                    #         )
                    #         if status_code == 410:
                    #             connections.delete_item(
                    #                 Key={"connectionId": item["connectionId"]}
                    #             )
                    #         else:
                    #             self.response["body"] = "Connection error"
                    #             self.response["statusCode"] = 500


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
                return self.send_response(content, status_code=500)
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
                return make_response("WebSocket connection error.", status_code=500)
            return make_response("OK", status_code=200)

        elif event_type == "MESSAGE":
            print("Message received")
            event_body = json.loads(event["body"])
            event_data = event_body["data"] or b""
            connections = get_connections()
            scope = self.get_scope_from_db(
                connection_id=connection_id, connections=connections
            )
            asgi_cycle = ASGIWebSocketCycle(scope, endpoint_url=endpoint_url)
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

            print("Starting cycle")
            asgi_cycle.put_message({"type": "websocket.connect"})
            asgi_cycle.put_message(message)
            response = asgi_cycle(self.app)
            print("Returning response")
            return response

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
