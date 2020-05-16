# Adapter

The heart of Mangum is the adapter class. It is a configurable wrapper that allows any [ASGI](https://asgi.readthedocs.io/en/latest/) application (or framework) to run in an [AWS Lambda](https://aws.amazon.com/lambda/) deployment. The adapter accepts a number of keyword arguments to configure settings related to logging, HTTP & WebSocket events, lifespan behaviour, and API Gateway.

```python
handler = Mangum(
    app,
    lifespan="auto",
    log_level="info",
    api_gateway_base_path=None,
    text_mime_types=None,
    dsn=None,
    api_gateway_endpoint_url=None,
    api_gateway_region_name=None
)
```

All arguments are optional, but some may be necessary for specific use-cases (e.g. `dsn` is only required for WebSocket support).

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

If you're using FastAPI it can be retrieved from the `scope` attribute of the request object.

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
