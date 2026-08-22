from __future__ import annotations

import json

from mangum import Mangum
from mangum.types import Receive, Scope, Send

LIFESPAN_STATE = {"startup_complete": False}


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                LIFESPAN_STATE["startup_complete"] = True
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    assert scope["type"] == "http"
    body = bytearray()
    while True:
        message = await receive()
        body.extend(message.get("body", b""))
        if not message.get("more_body", False):
            break

    response_body = json.dumps(
        {
            "method": scope["method"],
            "path": scope["path"],
            "query": scope["query_string"].decode(),
            "body_length": len(body),
            "lifespan_startup_complete": LIFESPAN_STATE["startup_complete"],
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"], [b"x-echo", b"mangum"]],
        }
    )
    await send({"type": "http.response.body", "body": response_body})


handler = Mangum(app, lifespan="auto")
