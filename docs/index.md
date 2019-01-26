# Mangum

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>

Mangum is a library for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with FaaS platforms.

**Important**: This project is under active development and in an experimental/unstable state.

## Requirements

Python 3.6+

## Installation

```shell
$ pip3 install mangum
```

## Dependencies

Currently there are two optional dependencies.

- [azure-functions](https://github.com/Azure/azure-functions-python-library) - Required for Azure.
- [boto3](https://github.com/boto/boto3) - Required for the AWS CLI commands.

This can be installed with:

```shell
$ pip3 install mangum[full]
```

## Supported Platforms

Only two platforms are currently supported, but if you'd like to see others, please open an issue.

### AWS Lambda / API Gateway

#### Example

Below is a basic ASGI application example using the AWS run method:

```python
from mangum.platforms.aws.adapter import run_asgi

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

def lambda_handler(event, context):
    return run_asgi(App, event, context)
```

#### Mangum CLI (experimental)

Experimental AWS packaging/deployment support to generate, package, and deploy an application. This requires installation of the optional dependencies for AWS:

```shell
$ pip install mangum[full]
```

It also requires the AWS CLI and AWS credentials.

The available commands are briefly outlined below, but there is also a quickstart guide [here](https://erm.github.io/mangum/aws-how-to/):

* `mangum init` - Create a new application and deployment configuration.

* `mangum package` - Package the local project to prepare for deployment.

* `mangum deploy` - Deploy the packaged application to AWS.

* `mangum tail` - Tail the last 10 minutes of CloudWatch for the function.

* `mangum describe` - Retrieve the API endpoints for the function.

### Azure Functions

#### Example

The same example application as above may be used with the Azure run method:

```python
from mangum.platforms.azure.adapter import run_asgi


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

def lambda_handler(req):
    return run_asgi(App, req)
```

The command-line tools for Azure Functions can do pretty much everything you need. A basic quickstart guide for using it with Mangum is outlined [here](https://erm.github.io/mangum/azure-how-to/).
