# Adapter

The heart of Mangum is the adapter class. It is a configurable wrapper that allows any [ASGI](https://asgi.readthedocs.io/en/latest/) application (or framework) to run in an [AWS Lambda](https://aws.amazon.com/lambda/) deployment. The adapter accepts a number of keyword arguments to configure settings related to logging, HTTP responses, ASGI lifespan, and API Gateway configuration.

```python
handler = Mangum(
    app,
    lifespan="auto",
    api_gateway_base_path=None,
    custom_handlers=None,
    text_mime_types=None,
)
```

All arguments are optional.

## Configuring an adapter instance

::: mangum.adapter.Mangum
    :docstring:

## Creating an AWS Lambda handler

The adapter can be used to wrap any application without referencing the underlying methods. It defines a `__call__` method that allows the class instance to be used as an AWS Lambda event handler function. 

```python
from mangum import Mangum
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}


handler = Mangum(app)
```

However, this is just one convention, you may also intercept events and construct the adapter instance separately. This may be useful if you need to implement custom event handling. The `handler` in the example above could be replaced with a function.

```python
def handler(event, context):
    if event.get("some-key"):
        # Do something or return, etc.
        return

    asgi_handler = Mangum(app)
    response = asgi_handler(event, context) # Call the instance with the event arguments

    return response
```

## Retrieving the AWS event and context

The AWS Lambda handler `event` and `context` arguments are made available to an ASGI application in the ASGI connection scope.

```python
scope['aws.event']
scope['aws.context']
```

For example, if you're using FastAPI it can be retrieved from the `scope` attribute of the request object.

```python
from fastapi import FastAPI
from mangum import Mangum
from starlette.requests import Request

app = FastAPI()


@app.get("/")
def hello(request: Request):
    return {"aws_event": request.scope["aws.event"]}

handler = Mangum(app)
```

## Custom Handlers

Mangum supports custom handlers to process Lambda events that don't match the built-in handlers (API Gateway, ALB, Lambda@Edge). This is useful for handling custom event formats or integrating with other AWS services.

### Basic Custom Handler

A custom handler must implement the following interface:

```python
from mangum import Mangum
from mangum.protocols import HTTPCycle
from mangum.types import Cycle, LambdaConfig, LambdaContext, LambdaEvent, Response, Scope


class MyCustomHandler:
    @classmethod
    def infer(cls, event: LambdaEvent, context: LambdaContext, config: LambdaConfig) -> bool:
        """Return True if this handler should process the event."""
        return "my-custom-key" in event

    def __init__(self, event: LambdaEvent, context: LambdaContext, config: LambdaConfig) -> None:
        self.event = event
        self.context = context
        self.config = config

    @property
    def cycle_cls(self) -> type[Cycle]:
        """Return the cycle class to use for request/response processing."""
        return HTTPCycle

    @property
    def body(self) -> bytes:
        """Return the request body."""
        return self.event.get("body", b"")

    @property
    def scope(self) -> Scope:
        """Return the ASGI scope dictionary."""
        return {
            "type": "http",
            "http_version": "1.1",
            "method": self.event.get("method", "GET"),
            "headers": [],
            "path": self.event.get("path", "/"),
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "query_string": b"",
            "server": ("localhost", 443),
            "client": ("127.0.0.1", 0),
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "aws.event": self.event,
            "aws.context": self.context,
        }

    def __call__(self, response: Response) -> dict:
        """Transform the ASGI response to a Lambda response."""
        return {
            "statusCode": response["status"],
            "headers": {k.decode(): v.decode() for k, v in response["headers"]},
            "body": response["body"].decode(),
        }


handler = Mangum(app, custom_handlers=[MyCustomHandler])
```

Custom handlers are checked **before** the built-in handlers, so they take priority.

### Custom Protocol Cycle

The `cycle_cls` property allows you to specify a custom request/response cycle class. This is useful for implementing custom protocols or adding middleware-like behavior at the cycle level.

```python
from mangum.protocols import HTTPCycle
from mangum.types import ASGI, Cycle, Response, Scope


class MyCustomCycle:
    """A custom cycle that adds behavior to the standard HTTP cycle."""

    def __init__(self, scope: Scope, body: bytes) -> None:
        self.scope = scope
        self._http_cycle = HTTPCycle(scope, body)

    async def __call__(self, app: ASGI) -> Response:
        # Add custom logic before/after the request
        return await self._http_cycle(app)


class MyCustomHandler:
    # ... other methods ...

    @property
    def cycle_cls(self) -> type[Cycle]:
        return MyCustomCycle
```
