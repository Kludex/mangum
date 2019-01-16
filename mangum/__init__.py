import asyncio
import enum
import urllib.parse


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

            body = message["body"].decode("utf-8")
            more_body = message.get("more_body")

            self.response["body"] = message["body"].decode("utf-8")

            if not more_body:
                self.state = ASGICycleState.CLOSED

        if self.state is ASGICycleState.CLOSED:
            self.put_message({"type": "http.disconnect"})
        # body = event["body"]
        # if event["isBase64Encoded"]:
        #     body = base64.standard_b64decode(body)
        # return {"type": "http.request", "body": body, "more_body": False}


def asgi_response(app, event, context):

    headers = event["headers"] or {}
    scheme = headers.get("X-Forwarded-Proto", "http")
    method = event["httpMethod"]
    path = event["path"]
    host = headers.get("Host")
    x_forwarded_port = headers.get("X-Forwarded-Port")

    if not any((host, x_forwarded_port)):
        server = None
    else:
        server = (host, int(x_forwarded_port))

    # client = headers.get("X-Forwarded-For", None)
    client = None

    query_string = event["queryStringParameters"]
    if query_string:
        query_string = urllib.parse.urlencode(query_string)

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
    asgi_cycle = ASGICycle(scope)
    asgi_instance = app(asgi_cycle.scope)
    asgi_task = loop.create_task(asgi_instance(asgi_cycle.receive, asgi_cycle.send))
    asgi_cycle.put_message({"type": "http.request", "body": b""})
    loop.run_until_complete(asgi_task)

    return asgi_cycle.response
