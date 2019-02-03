import base64
import asyncio
import enum
import traceback
import urllib.parse
from dataclasses import dataclass, field
from typing import Any


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


@dataclass
class ASGICycle:
    scope: dict
    body: bytes = b""
    state: ASGICycleState = ASGICycleState.REQUEST
    app_queue: asyncio.Queue = None
    response: dict = field(default_factory=dict)
    binary: bool = False

    def __call__(self, app, body: bytes = b"") -> dict:
        """
        Receives the application and any body included in the request, then builds the
        ASGI instance using the connection scope.

        Runs until the response is completey read from the application.
        """
        loop = asyncio.new_event_loop()
        self.app_queue = asyncio.Queue(loop=loop)
        self.put_message({"type": "http.request", "body": body, "more_body": False})
        asgi_instance = app(self.scope)
        asgi_task = loop.create_task(asgi_instance(self.receive, self.send))
        loop.run_until_complete(asgi_task)
        return self.response

    def put_message(self, message: dict) -> None:
        self.app_queue.put_nowait(message)

    async def receive(self) -> dict:
        """
        Awaited by the application to receive messages in the queue.
        """
        message = await self.app_queue.get()
        return message

    async def send(self, message: dict) -> None:
        """
        Awaited by the application to send messages to the current cycle instance.
        """
        message_type = message["type"]

        if self.state is ASGICycleState.REQUEST:
            if message_type != "http.response.start":
                raise RuntimeError(
                    f"Expected 'http.response.start', received: {message_type}"
                )

            status_code = message["status"]
            headers = {k: v for k, v in message.get("headers", [])}

            self.on_request(headers, status_code)
            self.state = ASGICycleState.RESPONSE

        elif self.state is ASGICycleState.RESPONSE:
            if message_type != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message_type}"
                )

            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            # The body must be completely read before returning the response.
            self.body += body

            if not more_body:
                self.on_response()
                self.put_message({"type": "http.disconnect"})

    def on_request(self, headers: dict, status_code: int) -> None:
        """
        Build the response headers for AWS.
        """
        self.response["statusCode"] = status_code
        self.response["isBase64Encoded"] = self.binary
        self.response["headers"] = {k.decode(): v.decode() for k, v in headers.items()}

    def on_response(self) -> None:
        """
        Build the response body for AWS.
        """
        body = self.body
        if self.binary:
            body = base64.b64encode(body)
        self.response["body"] = body.decode()


@dataclass
class Mangum:

    app: Any
    debug: bool = False

    def __call__(self, *args, **kwargs) -> Any:
        try:
            response = self.asgi(*args, **kwargs)
        except Exception as exc:
            if self.debug:
                content = traceback.format_exc()
                return self.send_response(content, status_code=500)
            raise exc
        else:
            return response

    def asgi(self, event: dict, context: dict) -> dict:
        """
        Entrypoint for the request event from AWS. Handles parsing the scope values and
        creating the ASGI instance, finally returning the instance response.
        """
        method = event["httpMethod"]
        headers = event["headers"] or {}
        path = event["path"]
        scheme = headers.get("X-Forwarded-Proto", "http")
        query_string_params = event["queryStringParameters"]
        query_string = (
            urllib.parse.urlencode(query_string_params).encode()
            if query_string_params
            else b""
        )

        client_addr = event["requestContext"].get("identity", {}).get("sourceIp", None)
        client = (client_addr, 0)
        server_addr = headers.get("Host", None)
        if server_addr is not None:
            if ":" not in server_addr:
                server_port = 80
            else:
                server_port = int(server_addr.split(":")[1])

            server = (server_addr, server_port)
        else:
            server = None  # pragma: no cover

        scope = {
            "server": server,
            "client": client,
            "scheme": scheme,
            "root_path": "",
            "query_string": query_string,
            "headers": [[k.lower().encode(), v.encode()] for k, v in headers.items()],
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
        }

        binary = event.get("isBase64Encoded", False)
        body = event["body"] or b""

        if binary:
            body = base64.b64decode(body)
        elif not isinstance(body, bytes):
            body = body.encode()

        response = ASGICycle(scope, binary=binary)(self.app, body=body)
        return response

    def send_response(self, content: str, status_code: int = 500) -> None:
        """
        Sends a server response, used in debugging.
        """
        return {
            "statusCode": status_code,
            "isBase64Encoded": False,
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "body": content,
        }
