import asyncio
import enum


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


class ASGICycle:
    def __init__(self, scope: dict, loop: asyncio.BaseEventLoop) -> None:
        self.scope = scope
        self.app_queue = asyncio.Queue(loop=loop)
        self.state = ASGICycleState.REQUEST
        self.response = {}

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
            headers = message.get("headers", [])

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
        raise NotImplementedError()

    def on_response_body(self, body: str) -> None:
        raise NotImplementedError()


class ASGIHandler:
    asgi_cycle_class = None

    def __init__(self, scope: dict) -> None:
        self.scope = scope

    def __call__(self, app, message: dict) -> dict:
        loop = asyncio.new_event_loop()
        asgi_cycle = self.asgi_cycle_class(self.scope, loop=loop)
        asgi_cycle.put_message(message)
        asgi_instance = app(asgi_cycle.scope)
        asgi_task = loop.create_task(asgi_instance(asgi_cycle.receive, asgi_cycle.send))
        loop.run_until_complete(asgi_task)
        return asgi_cycle.response
