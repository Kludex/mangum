# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>


Mangum is a library for adapting [ASGI](https://asgi.readthedocs.io/en/latest/) applications to use on FaaS platforms.

**Important**: This project is under active development and in an experimental/unstable state.

## Supported Platforms

- AWS Lambda + API Gateway
- Azure Functions

## Requirements

Python 3.6+

## Installation

```pip3 install mangum```

## Dependencies

Currently the only optional dependency is:

- [azure-functions](https://github.com/Azure/azure-functions-python-library) - Required for `azure_handler`.

## Example

Below is a basic ASGI application example that can be used with handler methods:

```python
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
```

### AWS Lambda + API Gateway

```python
from mangum.handlers.aws import aws_handler

def asgi_handler(event, context):
    return aws_handler(App, event, context)
```

### Azure Functions

```python
from mangum.handlers.azure import azure_handler

def asgi_handler(req):
    return azure_handler(App, req)

```
