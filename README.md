# Mangum

**Documentation**: https://erm.github.io/mangum/

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

```pip3 install mangum```

## Dependencies

Currently there are two optional dependencies.

- [azure-functions](https://github.com/Azure/azure-functions-python-library) - Required for `azure_handler`.
- [boto3](https://github.com/boto/boto3) - Required for the `mangum` CLI commands.

This can be installed with:

```pip3 install mangum[full]```

## Supported Platforms

Only two platforms are currently support.

### AWS Lambda / API Gateway

#### Example

Below is a basic ASGI application example that can be used with the handler methods:

```python
from mangum.handlers.aws import aws_handler

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
    return aws_handler(App, event, context)
```

#### Mangum CLI (experimental)

Experimental AWS packaging/deployment support. It generally works, but needs to be tested:

**Requirements**:

- AWS CLI & credentials
- Python 3

To quickly generate an app via the command-line, you may use the following command:

```shell
mangum init
```

This generates the following:

* A boilerplate ASGI app with the `mangum` package installed for deployment to AWS.
    
* A `settings.json` file with the generated AWS resource information.

* An S3 bucket to be used with the app.

* A `template.yaml` [SAM template](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-template-basics.html).

Once generated you'll have an app structure that looks like this:

```shell
├── README.md
├── hello_asgi
│   ├── app.py
│   ├── mangum
│   ├── mangum-0.3.0-py3.7.egg-info
│   ├── requirements.txt
│   └── template.yaml
└── settings.json
```

You will then be prompted to enter the following commands, these are simply wrappers around the AWS-CLI commands with the `settings.json` values generated previously as arguments.

```shell
magnum package
```

After packaging, you then can deploy:

```shell
mangum deploy
```

Full output example:

```
(venv37) [erm@iserlohn aws-test]$ ls
README.md   hello_asgi  settings.json
(venv37) [erm@iserlohn aws-test]$ mangum package
Packaging...
Successfully packaged. Run 'mangum deploy' to deploy it now.
(venv37) [erm@iserlohn aws-test]$ mangum deploy
Deploying! This may take some time...
API endpoints available at:
* https://1234abcd.execute-api.ap-southeast-1.amazonaws.com/Prod
* https://1234abcd.execute-api.ap-southeast-1.amazonaws.com/Stage
```

### Azure Functions

#### Example
The same example application above may be used with Azure Functions:

```python
from mangum.handlers.azure import azure_handler


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
    return azure_handler(App, req)
```

The command-line tools for Azure Functions can do pretty much everything you need. A basic quickstart guide for using it with Mangum is outlined [here](https://erm.github.io/mangum/azure-how-to/).
