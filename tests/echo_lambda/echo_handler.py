from __future__ import annotations

from mangum import Mangum
from mangum.types import Receive, Scope, Send


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    assert scope["type"] == "http"
    body = bytearray()
    while True:
        message = await receive()
        body.extend(message.get("body", b""))
        if not message.get("more_body", False):
            break

    response_body = b'{"method": "%s", "path": "%s", "query": "%s", "body_length": %d}' % (
        scope["method"].encode(),
        scope["path"].encode(),
        scope["query_string"],
        len(body),
    )
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"], [b"x-echo", b"mangum"]],
        }
    )
    await send({"type": "http.response.body", "body": bytes(response_body)})


handler = Mangum(app, lifespan="off")
