# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/mangum.svg?style=flat-square">

Mangum is an adapter for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with AWS Lambda & API Gateway. It is intended to provide an easy-to-use, configurable wrapper for any ASGI application deployed in an AWS Lambda function to handle API Gateway requests and responses.

## Features

- API Gateway support for [HTTP](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html), [REST](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html), and [WebSocket](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html) APIs.

- Multiple storage backend interfaces for managing WebSocket connections.

- Compatibility with ASGI application frameworks, such as [Starlette](https://www.starlette.io/), [FastAPI](https://fastapi.tiangolo.com/), and [Quart](https://pgjones.gitlab.io/quart/). 

- Works with existing deployment and configuration tools, including [Serverless Framework](https://www.serverless.com/) and [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html).

- Startup and shutdown [lifespan](https://asgi.readthedocs.io/en/latest/specs/lifespan.html) events.

## Requirements

Python 3.6+

## Installation

```shell
pip install mangum
```

You can install the required dependencies for the WebSocket backends with one the following:

```shell
pip install mangum[aws]
pip install mangum[postgresql]
```

## Examples

The examples below are "raw" ASGI applications with minimal configuration. Please read the [HTTP](https://erm.github.io/mangum/http/) and [WebSocket](https://erm.github.io/mangum/websockets/) docs for more details about configuration.

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

async def app(scope, receive, send):
    await send({"type": "websocket.accept", "subprotocol": None})
    await send({"type": "websocket.send", "text": "Hello world!"})
    await send({"type": "websocket.send", "bytes": b"Hello world!"})
    await send({"type": "websocket.close", "code": 1000})

handler = Mangum(
    app,
    ws_config={
        "backend": "s3",
        "params": {
            "bucket": "connections"
        }
    }
)
```
