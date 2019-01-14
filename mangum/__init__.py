import asyncio


class ASGILambdaCycle:
    def __init__(self, scope, loop):
        self.scope = scope
        self.app_queue = asyncio.Queue(loop=loop)
        self.response = {}

    async def receive(self) -> dict:
        message = await self.app_queue.get()
        # body = event["body"]
        # if event["isBase64Encoded"]:
        #     body = base64.standard_b64decode(body)
        # return {"type": "http.request", "body": body, "more_body": False}

        return message

    async def send(self, message) -> None:

        if message["type"] == "http.response.start":
            self.response["statusCode"] = message["status"]
            self.response["isBase64Encoded"] = False
            self.response["headers"] = {
                k.decode("utf-8"): v.decode("utf-8") for k, v in message["headers"]
            }
        if message["type"] == "http.response.body":
            self.response["body"] = message["body"].decode("utf-8")


def asgi_response(app, event, context):

    headers = event["headers"] or {}
    scheme = headers.get("X-Forwarded-Proto", "http")
    method = event["httpMethod"]
    path = event["path"]
    server = None
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
    asgi_cycle = ASGILambdaCycle(scope, loop=loop)
    asgi_instance = app(asgi_cycle.scope)
    asgi_task = loop.create_task(asgi_instance(asgi_cycle.receive, asgi_cycle.send))
    asgi_cycle.app_queue.put_nowait(
        {"type": "http.request", "body": b"", "more_body": False}
    )
    loop.run_until_complete(asgi_task)

    return asgi_cycle.response
