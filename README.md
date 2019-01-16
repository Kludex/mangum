# mangum

An attempt to provide simple AWS Lambda support to any ASGI application.

Work in progress.

## Example

```python
from mangum import asgi_response


class App:
    def __init__(self, scope) -> None:
        self.scope = scope

    async def __call__(self, receive, send) -> None:
        message = await receive()
        if message["type"] == "http.request":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello, world!"})


def lambda_handler(event, context):
    return asgi_response(App, event, context)

```

## Todo

- WebSocket support through API Gateway
- Chunked responses/streaming
- Tests
- Detailed instructions
