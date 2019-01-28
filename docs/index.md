# Mangum

**Documentation**: https://erm.github.io/mangum/

<a href="https://pypi.org/project/mangum/">
    <img src="https://badge.fury.io/py/mangum.svg" alt="Package version">
</a>
<a href="https://travis-ci.org/erm/mangum">
    <img src="https://travis-ci.org/erm/mangum.svg?branch=master" alt="Build Status">
</a>

Mangum is a library for using [ASGI](https://asgi.readthedocs.io/en/latest/) applications with FaaS platforms.

## Requirements

Python 3.6+

## Installation

```shell
$ pip3 install mangum
```

## Supported Platforms

Only two platforms are currently supported, but if you'd like to see others, please open an issue.

### AWS Lambda / API Gateway

To make an ASGI application compatible with AWS Lambda & AWS Gateway, wrap it in the `AWSLambdaMiddleware`:

```python
from mangum.platforms.aws.middleware import AWSLambdaMiddleware
from yourapp.app import app


handler = AWSLambdaMiddleware(app)  # optionally set debug=True
```

For this example, you would need to specify your lambda event handler as `asgi.handler`. 

**Note**: This platform middleware can also use an optional `debug` argument to return unhandled errors raised by the application. It should NOT be enabled outside of development.

### Azure Functions

Similarly as above, wrap the application using the `AzureFunctionMiddleware`:

```python
from mangum.platforms.azure.middleware import AzureFunctionMiddleware
from yourapp.app import app

handler = AzureFunctionMiddleware(app)
```

A basic quickstart guide for using Azure Functions with Mangum is outlined [here](https://erm.github.io/mangum/azure-how-to/).

## Dependencies

There are required/optional dependencies for specific platforms being used, but the base install does not have any hard requirements:

`azure-functions` - *required* for Azure Function support. Can be installed using:

```shell
$ pip3 install mangum[azure]
```

`boto3`, `click` - *required* for the AWS-specific CLI tools (this is NOT required in deployments):

```shell
$ pip3 install mangum[aws]
```

Everything can be installed with:

```shell
$ pip3 install mangum[full]
```

### Mangum CLI (experimental)

Experimental AWS packaging/deployment support. This requires installation of the optional dependencies for AWS:

```shell
$ pip install mangum[full]
```

It also requires:

- AWS CLI
- AWS credentials.

The available commands are briefly outlined below, but there is also a quickstart guide [here](https://erm.github.io/mangum/aws-how-to/):

* `mangum aws init` - Create a new configuration template for an application.

* `mangum aws build` - Install the requirements and copy the application files into the build directory.

* `mangum aws package` - Package the local project to prepare for deployment.

* `mangum aws deploy` - Deploy the packaged application to AWS.

* `mangum aws tail` - Tail the last 10 minutes of CloudWatch for the function.

* `mangum aws describe` - Retrieve the API endpoints for the function.

* `mangum aws validate` - Validate the SAM template in the current configuration.
