import asyncio
import enum


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


class ASGIHTTPCycle:
    def __init__(self, scope) -> None:
        self.scope = scope
        self.app_queue = asyncio.Queue()
        self.state = ASGICycleState.REQUEST
        self.response = {}

    def put_message(self, message) -> None:
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

            self.response["statusCode"] = status_code
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

            self.put_message({"type": "http.disconnect"})
