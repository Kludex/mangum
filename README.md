# Mangum

Serverless [ASGI](https://asgi.readthedocs.io/en/latest/) adapters. ***Work in progress***

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>

## Supported Platforms

- AWS Lambda + API Gateway
- Azure Functions

**Requirements**: Python 3.6+

## Installation

```pip install mangum```

**Note**: This project is experimental/unstable and under active development.

## Examples


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

### AWS Lambda/API Gateway

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
    return func.HttpResponse(**response)

```
