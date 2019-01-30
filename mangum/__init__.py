import base64
import asyncio
import enum
import traceback
import urllib.parse
from typing import Any


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


class ASGICycle:
    def __init__(self, scope: dict, binary: bool = False) -> None:
        self.scope = scope
        self.body = b""
        self.state = ASGICycleState.REQUEST
        self.app_queue = None
        self.response = {}
        self.binary = binary

    def __call__(self, app, body: bytes = b"") -> dict:
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
        message = await self.app_queue.get()
        return message

    async def send(self, message: dict) -> None:
        message_type = message["type"]

        if self.state is ASGICycleState.REQUEST:
            if message_type != "http.response.start":
                raise RuntimeError(
                    f"Expected 'http.response.start', received: {message_type}"
                )

            status_code = message["status"]
            headers = {k: v for k, v in message.get("headers", [])}

            self.on_response_start(headers, status_code)
            self.state = ASGICycleState.RESPONSE

        elif self.state is ASGICycleState.RESPONSE:
            if message_type != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message_type}"
                )

            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            self.body += body

            if not more_body:
                self.on_response_close()
                self.put_message({"type": "http.disconnect"})

    def on_response_start(self, headers: dict, status_code: int) -> None:
        self.response["statusCode"] = status_code
        self.response["isBase64Encoded"] = self.binary
        self.response["headers"] = {k.decode(): v.decode() for k, v in headers.items()}

    def on_response_close(self) -> None:
        body = self.body
        if self.binary:
            body = base64.b64encode(body)
        self.response["body"] = body.decode()


class Mangum:
    def __init__(self, app, debug: bool = False) -> None:
        self.app = app
        self.debug = debug

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
        server_addr = headers.get("Host", "mangum")
        if ":" not in server_addr:
            server_port = 80
        else:
            server_port = int(server_addr.split(":")[1])

        server = (server_addr, server_port)

        scope = {
            "server": server,
            "client": client,
            "scheme": scheme,
            "root_path": "",
            "query_string": query_string,
            "headers": [[k.encode(), v.encode()] for k, v in headers.items()],
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
        return {
            "statusCode": status_code,
            "isBase64Encoded": False,
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "body": content,
        }
