# mangum

AWS Lambda/API Gateway support for ASGI applications.

***Work in progress***

Currently only supports HTTP responses, but there is an open issue [here](https://github.com/erm/mangum/issues/1) here for working out potential WebSocket support.

## Installation

```pip install mangum```

**Note**: The package on PyPi may be significantly behind the active development, so you probably want to clone the repo instead.

## Examples

Below is a basic "hello world" ASGI application:

```python
from mangum import asgi_handler


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
    return asgi_handler(App, event, context)

```

Any ASGI framework should work as well, here is the above example using [Starlette](https://github.com/encode/starlette/):

```python
from mangum import asgi_handler
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

app = Starlette()

@app.route("/")
def homepage(request):
    return PlainTextResponse("Hello, world!")

def lambda_handler(event, context):
    return asgi_handler(app, event, context)

```
