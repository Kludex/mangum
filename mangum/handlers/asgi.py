import asyncio
import enum


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


class ASGICycle:
    def __init__(self, scope: dict, body: bytes = b"") -> None:
        self.scope = scope
        self.body = body
        self.state = ASGICycleState.REQUEST
        self.app_queue = None
        self.response = {}

    def __call__(self, app) -> dict:
        loop = asyncio.new_event_loop()

        self.app_queue = asyncio.Queue()
        self.put_message({"type": "http.request", "body": self.body})

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
            headers = {
                k.decode("utf-8"): v.decode("utf-8")
                for k, v in message.get("headers", [])
            }

            self.on_response_start(headers, status_code)
            self.state = ASGICycleState.RESPONSE

        elif self.state is ASGICycleState.RESPONSE:
            if message_type != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message_type}"
                )

            body = message["body"]
            if isinstance(body, bytes):
                body = body.decode("utf-8")

            self.on_response_body(body)
            self.put_message({"type": "http.disconnect"})

    def on_response_start(self, headers: list, status_code: int) -> None:
        raise NotImplementedError()  # pragma: no cover

    def on_response_body(self, body: str) -> None:
        raise NotImplementedError()  # pragma: no cover
