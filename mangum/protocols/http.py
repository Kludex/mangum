import urllib.parse
import base64
import typing
from dataclasses import dataclass

from mangum.protocols.asgi import ASGICycle, ASGICycleState
from mangum.types import ASGIMessage, ASGIApp
from mangum.exceptions import ASGIWebSocketCycleException
from mangum.utils import get_server_and_client


@dataclass
class ASGIHTTPCycle(ASGICycle):

    body: bytes = b""

    async def asgi_send(self, message: ASGIMessage) -> None:
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


def handle_http(
    app: ASGIApp,
    event: typing.Dict[str, typing.Any],
    context: typing.Dict[str, typing.Any],
) -> typing.Dict[str, typing.Any]:
    server, client = get_server_and_client(event)
    headers = [[k.lower().encode(), v.encode()] for k, v in event["headers"].items()]
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
    asgi_cycle.put_message({"type": "http.request", "body": body, "more_body": False})
    response = asgi_cycle(app)
    return response
