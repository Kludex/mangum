# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/mangum.svg?style=flat-square">


Mangum is an adapter for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with AWS Lambda & API Gateway. It is intended to provide an easy-to-use, configurable wrapper for any ASGI application deployed in an AWS Lambda function to handle API Gateway requests and responses.

**Documentation**: [https://erm.github.io/mangum](https://erm.github.io/mangum)

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

## Example

```python3
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

## Usage

The adapter class `Mangum` accepts the following optional arguments:

- `enable_lifespan` : bool (default=True)
    
    Specify whether or not to enable lifespan support. The adapter will automatically determine if lifespan is supported by the framework unless explicitly disabled.

- `log_level` : str (default="info")
    
    Level parameter for the logger.

- `api_gateway_base_path` : str (default=None)
    
    Base path to strip from URL when using a custom domain name.

- `text_mime_types` : list (default=None)
        
    The list of MIME types (in addition to the defaults) that should not return binary responses in API Gateway.

- `ws_config` : dict (default=None)

    Configuration mapping for a supported WebSocket backend.

### Binary support

Binary response support is available depending on the `Content-Type` and `Content-Encoding` headers. The default text mime types are the following:

- `application/json`
- `application/javascript`
- `application/xml`
- `application/vnd.api+json`

All `Content-Type` headers starting with `text/` are included by default.

If the `Content-Encoding` header is set to `gzip`, then a binary response will be returned regardless of mime type.

Binary response bodies will be base64 encoded and `isBase64Encoded` will be `True`.

### Event and context

The AWS Lambda handler has `event` and `context` parameters. These are available in the ASGI `scope` object:

```python3
scope['aws.event']
scope['aws.context']
```

## WebSockets

Mangum provides support for [WebSocket API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html) events in API Gateway. The adapter class handles parsing the incoming requests and managing the ASGI cycle using a configured storage backend. 

You can learn more about WebSocket support in the [documentation](https://erm.github.io/mangum/websockets)

