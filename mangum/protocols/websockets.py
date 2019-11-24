import enum
import asyncio
from dataclasses import dataclass, field

from mangum.connections import ConnectionTable
from mangum.types import ASGIApp, Message, Scope
from mangum.exceptions import ASGIWebSocketCycleException


class ASGIState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class ASGIWebSocketCycle:

    scope: Scope
    endpoint_url: str
    connection_id: str
    connection_table: ConnectionTable
    state: ASGIState = ASGIState.REQUEST
    response: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()

    def __call__(self, app: ASGIApp) -> dict:
        asgi_instance = app(self.scope, self.receive, self.send)
        asgi_task = self.loop.create_task(asgi_instance)
        self.loop.run_until_complete(asgi_task)
        return self.response

    async def receive(self) -> Message:  # pragma: no cover
        message = await self.app_queue.get()
        return message

    async def send(self, message: Message) -> None:
        if self.state is ASGIState.REQUEST:
            if message["type"] in ("websocket.accept", "websocket.close"):
                self.state = ASGIState.RESPONSE
            else:
                raise RuntimeError(
                    f"Expected 'websocket.accept' or 'websocket.close', received: {message['type']}"
                )
        else:
            data = message.get("text", "")
            if message["type"] == "websocket.send":
                group = message.get("group", None)
                self.send_data(data=data, group=group)

    def send_data(self, *, data: str, group: str = None) -> None:  # pragma: no cover
        """
        Send a data message to a client or group of clients using the connection table.
        """
        item = self.connection_table.get_item(self.connection_id)
        if not item:
            raise ASGIWebSocketCycleException("Connection not found")

        if group:
            # Retrieve the existing groups for the current connection, or create a new
            # groups entry if one does not exist.
            groups = item.get("groups", [])
            if group not in groups:
                # Ensure the group specified in the message is included.
                groups.append(group)
                status_code = self.connection_table.update_item(
                    self.connection_id, groups=groups
                )
                if status_code != 200:
                    raise ASGIWebSocketCycleException("Error updating groups")

            # Retrieve all items associated with the current group.
            items = self.connection_table.get_group_items(group)
            if items is None:
                raise ASGIWebSocketCycleException("No connections found")
        else:
            # Single send, add the current item to a list to be iterated by the
            # connection table.
            items = [item]
        self.connection_table.send_data(
            items, endpoint_url=self.endpoint_url, data=data
        )
