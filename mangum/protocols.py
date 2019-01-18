import asyncio
import enum
import urllib.parse


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()
    CLOSED = enum.auto()


class ASGIHTTPCycle:
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


class ASGIWebSocketCycle:
    def __init__(self, scope: dict, callback_url: str, connection_id: str) -> None:
        self.scope = scope
        self.app_queue = asyncio.Queue()
        self.callback_url = callback_url
        self.connection_id = connection_id
        self.response = {}

    def put_message(self, message) -> None:
        self.app_queue.put_nowait(message)

    async def receive(self) -> dict:
        message = await self.app_queue.get()
        return message

    async def send(self, message) -> None:
        message_type = message["type"]
        if message_type == "websocket.accept":

            print("accept")

        if message_type == "websocket.send":
            # handle send
            print("send")

            if "bytes" in message:
                data = message["bytes"]

            if "text" in message:
                data = message["text"]

            print(data)

        elif message_type == "websocket.close":
            # handle close
            print("close")
