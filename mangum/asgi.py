import enum
import asyncio
import base64
from dataclasses import dataclass, field

from mangum.connections import ConnectionTable
from mangum.types import ASGIScope, ASGIMessage, ASGIApp
from mangum.exceptions import ASGIWebSocketCycleException


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
    connection_id: str = None
    connection_table: ConnectionTable = None

    async def send(self, message: ASGIMessage) -> None:
        if self.state is ASGICycleState.REQUEST:
            if message["type"] in ("websocket.accept", "websocket.close"):
                self.state = ASGICycleState.RESPONSE
            else:
                raise RuntimeError(
                    f"Expected 'websocket.accept' or 'websocket.close', received: {message['type']}"
                )
        else:
            data = message.get("text")
            if message["type"] == "websocket.send":
                group = message.get("group", None)
                self.send_data(data=data, group=group)

    def send_data(self, *, data: str, group: str = None) -> None:
        item = self.connection_table.get(self.connection_id)
        if group:
            groups = item.get("groups", None)
            if groups is None:
                groups = []
            if group not in groups:
                groups.append(group)
                result = self.connection_table.set(
                    {"connectionId": self.connection_id, "groups": groups}
                )
                status_code = result.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if status_code != 200:
                    raise ASGIWebSocketCycleException("Error updating groups")
            items = self.connection_table.get_group_items(group)
            if items is None:
                raise ASGIWebSocketCycleException("No connections found")
        else:
            items = [items]
        self.connection_table.send(items, data=data)