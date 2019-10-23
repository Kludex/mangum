import typing
import json
from dataclasses import dataclass

from mangum.utils import make_response, get_server_and_client
from mangum.connections import ConnectionTable
from mangum.protocols.asgi import ASGICycle, ASGICycleState
from mangum.types import ASGIMessage, ASGIApp, AWSMessage
from mangum.exceptions import ASGIWebSocketCycleException


@dataclass
class ASGIWebSocketCycle(ASGICycle):

    endpoint_url: str = None
    connection_id: str = None
    connection_table: ConnectionTable = None

    async def asgi_send(self, message: ASGIMessage) -> None:
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


def handle_ws(app: ASGIApp, event: AWSMessage, context: AWSMessage) -> AWSMessage:
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
        headers = event["headers"]
        root_path = event["requestContext"]["stage"]
        scope = {
            "type": "websocket",
            "path": "/",
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
                "path": "/",
                "bytes": None,
                "text": event_data,
            }
        )
        try:
            asgi_cycle(app)
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

    return make_response("Error", status_code=500)
