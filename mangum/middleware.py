import json

from mangum.types import ASGIApp, Scope, Receive, Send, Message


class WebSocketMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert (
            scope["type"] == "websocket"
        ), f"WebSocketMiddleware called with invalid scope type '{scope['type']}'"
        scope["subscriptions"] = []

        async def websocket_send(message: Message) -> None:
            if message["type"] == "websocket.send":
                text = message.get("text", "")
                if text:
                    _data = json.loads(text)
                    message_type = _data.get("type")
                    if message_type in ("broadcast.publish", "broadcast.subscribe"):
                        channel = _data["channel"]
                        body = _data.get("body")
                        message = {
                            "type": message_type,
                            "channel": channel,
                            "body": body,
                        }

            await send(message)

        await self.app(scope, receive, websocket_send)
