# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/mangum.svg?style=flat-square">

Mangum is an adapter for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with AWS Lambda & API Gateway. It is intended to provide an easy-to-use, configurable wrapper for any ASGI application deployed in an AWS Lambda function to handle API Gateway requests and responses.

***Documentation***: https://mangum.io/

## Features

- API Gateway support for [HTTP](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html), [REST](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html), and [WebSocket](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html) APIs.

- Multiple storage backend interfaces for managing WebSocket connections.

- Compatibility with ASGI application frameworks, such as [Starlette](https://www.starlette.io/), [FastAPI](https://fastapi.tiangolo.com/), and [Quart](https://pgjones.gitlab.io/quart/). 

- Support for binary media types and payload compression in API Gateway.

- Works with existing deployment and configuration tools, including [Serverless Framework](https://www.serverless.com/) and [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html).

- Startup and shutdown [lifespan](https://asgi.readthedocs.io/en/latest/specs/lifespan.html) events.

## Requirements

Python 3.6+

## Installation

```shell
pip install mangum
```

## Usage

The `Mangum` adapter class is designed to wrap any ASGI application and returns a callable. It can wrap an application and be assigned as the handler:

```python
from mangum import Mangum

# Define an ASGI application

handler = Mangum(app)
```

However, this is just one convention, you may also intercept events and construct the adapter instance separately:

```python
def handler(event, context):
    if event.get("some-key"):
        # Do something or return, etc.

    asgi_handler = Mangum(app)
    response = asgi_handler(event, context) # Call the instance with the event arguments

    return response
```

## Configuration

The adapter accepts various arguments for configuring lifespan, logging, HTTP, WebSocket, and API Gateway behaviour.

```python
handler = Mangum(
    app,
    enable_lifespan=True,
    log_level="info",
    api_gateway_base_path=None,
    text_mime_types=None,
    dsn=None,
    api_gateway_endpoint_url=None,
    api_gateway_region_name=None
)
```

### Parameters

- `app` : ***ASGI application***

    An asynchronous callable that conforms to ASGI specification version 3.0. This will usually be a framework application instance that exposes a valid ASGI callable.

- `enable_lifespan` : **bool**
    
    Specify whether or not to enable lifespan support. The adapter will automatically determine if lifespan is supported by the framework unless explicitly disabled.

- `log_level` : **str**
    
    Level parameter for the logger.

- `api_gateway_base_path` : **str**
    
    Base path to strip from URL when using a custom domain name.

- `text_mime_types` : **list**
        
    The list of MIME types (in addition to the defaults) that should not return binary responses in API Gateway.

- `dsn`: **str**
    
    Connection string to configure a supported WebSocket backend.

- `api_gateway_endpoint_url` : **str**
    
    The endpoint url to use when sending data to WebSocket connections in API Gateway. This is useful if you are debugging locally with a package such as [serverless-offline](https://github.com/dherault/serverless-offline).

    Defaults to the `AWS_REGION` value in the AWS Lambda environment.

- `api_gateway_region_name` : **str**
    
    The region name of the API Gateway contains the connections created by WebSocket APIs.
    
    Defaults to the `AWS_REGION` value in the AWS Lambda environment.


### Event and context

The AWS Lambda handler has `event` and `context` parameters. These are available in the ASGI `scope` object:

```python
scope['aws.event']
scope['aws.context']
```


## Examples

The examples below are ASGI applications (non-framework) with minimal configurations. You should be able to replace the `app` in these example with most ASGI framework application instances. Please read the [HTTP](https://erm.github.io/mangum/http/) and [WebSocket](https://erm.github.io/mangum/websocket/) docs for more detailed configuration information.

### HTTP

```python
from mangum import Mangum

async def app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


handler = Mangum(app)
```

### WebSocket

```python
from mangum import Mangum

html = b"""
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("%s");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }


        </script>
    </body>
</html>
""" % os.environ.get("WEBSOCKET_URL", "ws://localhost:3000")

async def app(scope, receive, send):
    assert scope["type"] in ("http", "websocket")
    if scope["type"] == "http":
        message = await receive()
        if message["type"] == "http.request":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/html; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": html})
    if scope["type"] == "websocket":
        while True:
            message = await receive()
            if message["type"] == "websocket.connect":
                await send({"type": "websocket.accept"})

            if message["type"] == "websocket.receive":
                text = f"Received message: {message['text']}"
                await send({"type": "websocket.send", "text": text})

            if message["type"] == "websocket.disconnect":
                await send({"type": "websocket.close", "code": 1000})

handler = Mangum(
    app,
    dsn="s3://my-bucket-12345"
)
```
