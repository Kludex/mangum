# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/jordaneremieff/mangum">
    <img src="https://travis-ci.org/jordaneremieff/mangum.svg?branch=master" alt="Build Status">
</a>
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/mangum.svg?style=flat-square">

Mangum is an adapter for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with AWS Lambda & API Gateway. It is intended to provide an easy-to-use, configurable wrapper for any ASGI application deployed in an AWS Lambda function to handle API Gateway requests and responses.

***Documentation***: https://mangum.io/

## Features

- API Gateway support for [HTTP](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html) and [REST](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html) APIs.

- Compatibility with ASGI application frameworks, such as [Starlette](https://www.starlette.io/), [FastAPI](https://fastapi.tiangolo.com/), and [Quart](https://pgjones.gitlab.io/quart/). 

- Support for binary media types and payload compression in API Gateway using GZip or Brotli.

- Works with existing deployment and configuration tools, including [Serverless Framework](https://www.serverless.com/) and [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html).

- Startup and shutdown [lifespan](https://asgi.readthedocs.io/en/latest/specs/lifespan.html) events.

## Requirements

Python 3.6+

## Installation

```shell
pip install mangum
```

## Example

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

Or using a framework.

```python
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

handler = Mangum(app)
```
