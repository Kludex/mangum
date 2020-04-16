# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>

Mangum is an adapter for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with AWS Lambda & API Gateway.

**Documentation**: [https://erm.github.io/mangum](https://erm.github.io/mangum)

## Requirements

Python 3.6+

## Installation

```shell
pip install mangum
```

## Usage

The adapter class `Mangum` accepts the following optional arguments:

- `enable_lifespan` : bool (default=True)
    
    Specify whether or not to enable lifespan support.

- `api_gateway_base_path` : str (default=None)
    
    Base path to strip from URL when using a custom domain name.

- `text_mime_types` : list (default=None)
        
    The list of MIME types (in addition to the defaults) that should not return binary responses in API Gateway.

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


handler = Mangum(app, enable_lifespan=False) # disable lifespan for raw ASGI example
```

## WebSockets (experimental)

The adapter currently provides some basic WebSocket support using `boto3` with [DynamoDB](https://aws.amazon.com/dynamodb/). To install Mangum with the optional dependency:

```shell
pip install mangum[full]
```
