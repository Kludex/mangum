# Mangum

Serverless response handlers for ASGI applications.

***Work in progress***

Currently supports AWS Lambda/API Gateway and Azure Functions. Experimental/unstable. 

**Requirements: Python 3.6+**

## Installation

```pip install mangum```

**Note**: The package on PyPi may be significantly behind the active development, so you probably want to clone the repo instead.

## Example


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
    return func.HttpResponse(response["body"], status_code=response["status_code"])

```
