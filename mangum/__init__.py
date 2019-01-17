import asyncio
import enum
import urllib.parse
import base64


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()
    CLOSED = enum.auto()


class ASGICycle:
    def __init__(self, scope):
        self.scope = scope
        self.app_queue = asyncio.Queue()
        self.state = ASGICycleState.REQUEST
        self.response = {}

    def put_message(self, message) -> None:
        if self.state is ASGICycleState.CLOSED:
            return
        self.app_queue.put_nowait(message)

    async def receive(self) -> dict:
        message = await self.app_queue.get()
        return message

    async def send(self, message) -> None:
        message_type = message["type"]

        if self.state is ASGICycleState.REQUEST:
            if message_type != "http.response.start":
                raise RuntimeError(
                    f"Expected 'http.response.start', received: {message_type}"
                )

            status_code = message["status"]
            headers = message.get("headers", [])

            # We have received the headers and can now begin populating the initial part
            # of the response.
            self.response["statusCode"] = message["status"]
            self.response["isBase64Encoded"] = False
            self.response["headers"] = {
                k.decode("utf-8"): v.decode("utf-8") for k, v in headers
            }
            self.state = ASGICycleState.RESPONSE

        elif self.state is ASGICycleState.RESPONSE:
            if message_type != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message_type}"
                )

            # Handle setting the body in the response and complete the response.
            body = message["body"]
            if isinstance(body, bytes):
                body = body.decode("utf-8")

            self.response["body"] = body

            # TODO: Currently only handle sending a single body response, so this will
            # always be closed.
            # more_body = message.get("more_body")
            # if not more_body:
            #     self.state = ASGICycleState.CLOSED

            self.state = ASGICycleState.CLOSED

        if self.state is ASGICycleState.CLOSED:
            self.put_message({"type": "http.disconnect"})


def asgi_response(app, event, context):

    headers = event["headers"] or {}
    scheme = headers.get("X-Forwarded-Proto", "http")
    method = event["httpMethod"]
    path = event["path"]
    host = headers.get("Host")
    x_forwarded_port = headers.get("X-Forwarded-Port")

    # Build the server key based on the listening address and port, default to None.
    if not any((host, x_forwarded_port)):
        server = None
    else:
        server = (host, int(x_forwarded_port))

    # client = headers.get("X-Forwarded-For", None)
    client = None

    body = b""
    more_body = False
    # TODO
    # body = event.get("body", b"")
    # more_body = False
    # if body and event.get("isBase64Encoded"):
    #     body = base64.standard_b64decode(body)

    # If the query parameters are provided, then we need to encode them to bytes per the
    # ASGI spec, otherwise send empty bytes.
    query_string_params = event["queryStringParameters"]
    if query_string_params:
        query_string = urllib.parse.urlencode(query_string_params).encode()
    else:
        query_string = b""

    scope = {
        "type": "http",
        "http_version": "1.1",
        "server": server,
        "client": client,
        "scheme": scheme,
        "method": method,
        "root_path": "",
        "path": path,
        "query_string": query_string,
        "headers": headers.items(),
    }

    loop = asyncio.get_event_loop()

    # Create the ASGI cycle task using the scope built from the event with the app.
    asgi_cycle = ASGICycle(scope)
    asgi_instance = app(asgi_cycle.scope)
    asgi_task = loop.create_task(asgi_instance(asgi_cycle.receive, asgi_cycle.send))

    # Send the initial HTTP request message, optionally send the body data
    asgi_cycle.put_message(
        {"type": "http.request", "body": body, "more_body": more_body}
    )
    loop.run_until_complete(asgi_task)

    return asgi_cycle.response
