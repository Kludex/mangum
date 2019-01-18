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
