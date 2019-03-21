# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>

Mangum is a library for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with AWS Lambda & API Gateway.

**Status**: This project may face periods of inactivity from time to time, but PRs are welcomed.

## Requirements

Python 3.7+

## Installation

```shell
pip3 install mangum
```

## Usage

The adapter class `Mangum` accepts the following optional arguments:

* `debug` (bool, default=False) -
    
    If an exception is caught by the adapter class, then this will return a simple error response.


* `spec_version` (int, choices=[2, 3], default=3) -
    
    Select the specification version (ASGI2, ASGI3) to use for the application.

### Example

```python
from mangum import Mangum


class App:
    def __init__(self, scope):
        self.scope = scope

    async def __call__(self, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})



handler = Mangum(App)
```


## Frameworks

Any ASGI framework should work with Mangum, however there are cases where certain non-ASGI behaviour of an application will causes issues when deploying to a serverless platform.
