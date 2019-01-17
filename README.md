# mangum

An attempt to provide simple AWS Lambda/API Gateway support to any ASGI application.

Work in progress.

## Examples

### Plain ASGI

Below is a basic ASGI application that returns a "hello world" response:

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

### Starlette

Here is another example, this time using [Starlette](https://github.com/encode/starlette/), to demonstrate that the response method can be used with frameworks as well:

```python
from mangum import asgi_response
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

app = Starlette()

@app.route("/")
def homepage(request):
    return PlainTextResponse("Hello, world!")

def lambda_handler(event, context):
    return asgi_response(app, event, context)

```

## Todo

- WebSocket support through API Gateway
- Chunked responses/streaming
- More tests
- Detailed instructions
- More framework examples
- Lots
