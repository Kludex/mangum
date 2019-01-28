import asyncio
import enum
import cgi


class ASGICycleState(enum.Enum):
    REQUEST = enum.auto()
    RESPONSE = enum.auto()


class ASGICycle:
    def __init__(self, scope: dict, body: bytes = b"", **kwargs) -> None:
        """
        Base for implementing the ASGI application request-response cycle for a
        particular FaaS platform.
        """
        self.scope = scope
        self.body = body
        self.state = ASGICycleState.REQUEST
        self.app_queue = None
        self.response = {}
        self.charset = None
        self.mimetype = None

    def __call__(self, app) -> dict:
        """
        Run the event loop and instantiate the ASGI application for the current request.
        """
        loop = asyncio.new_event_loop()
        self.app_queue = asyncio.Queue(loop=loop)
        self.put_message({"type": "http.request", "body": self.body})
        asgi_instance = app(self.scope)
        asgi_task = loop.create_task(asgi_instance(self.receive, self.send))
        loop.run_until_complete(asgi_task)
        return self.response

    def put_message(self, message: dict) -> None:
        self.app_queue.put_nowait(message)

    async def receive(self) -> dict:
        """
        An awaitable used by the application to receive messages from the queue.
        """
        message = await self.app_queue.get()
        return message

    async def send(self, message: dict) -> None:
        """
        An awaitable used by the application to send messages to the handler.
        """
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

            if "content-type" in headers:
                mimetype, options = cgi.parse_header(headers["content-type"])
                charset = options.get("charset", None)
                if charset:
                    self.charset = charset
                if mimetype:
                    self.mimetype = mimetype

            self.on_response_start(headers, status_code)
            self.state = ASGICycleState.RESPONSE

        elif self.state is ASGICycleState.RESPONSE:
            if message_type != "http.response.body":
                raise RuntimeError(
                    f"Expected 'http.response.body', received: {message_type}"
                )

            body = message["body"]

            self.on_response_body(body)
            self.put_message({"type": "http.disconnect"})

    def on_response_start(self, headers: list, status_code: int) -> None:
        """
        Handles the `http.response.start` event and begins building the response.
        """
        raise NotImplementedError()  # pragma: no cover

    def on_response_body(self, body: str) -> None:
        """
        Handles the `http.response.body` event and completes the response.
        """
        raise NotImplementedError()  # pragma: no cover
