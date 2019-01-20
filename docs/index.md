# Mangum

<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>

Mangum is a library for adapting [ASGI](https://asgi.readthedocs.io/en/latest/) applications for use in FaaS platforms.

**Important**: This project is under active development and in an experimental/unstable state.

## Supported Platforms

- AWS Lambda + API Gateway
- Azure Functions

## Requirements

Python 3.6+

## Installation

```pip3 install mangum```

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

def lambda_handler(event, context):
    return aws_handler(App, event, context)
```

### Azure Functions

```python
from mangum.handlers.azure import azure_handler
import azure.functions as func

def main(req):
    response = azure_handler(App, req)
    return func.HttpResponse(response["body"], status_code=response["status_code"])

```
