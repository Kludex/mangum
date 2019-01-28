# Mangum

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

Only two platforms are currently supported, but if you'd like to see others, please open an [issue](https://github.com/erm/mangum/issues).

### AWS Lambda / API Gateway

To make an ASGI application compatible with AWS Lambda & API Gateway, wrap it with the `AWSLambdaAdapter`:

```python
from mangum.platforms.aws.adapter import AWSLambdaAdapter
from yourapp.app import app


handler = AWSLambdaAdapter(app)  # optionally set debug=True
```

You would then need to specify `<path>.handler` in your AWS Lambda configuration.

**Note**: This platform adapter can also use an optional `debug` argument to return unhandled errors raised by the application. It should NOT be enabled outside of development.

An example application can be found [here](https://github.com/erm/asgi-examples/tree/master/mangum/aws).

### Azure Functions

Similarly as above, wrap the application with the `AzureFunctionAdapter`:

```python
from mangum.platforms.azure.adapter import AzureFunctionAdapter
from yourapp.app import app


handler = AzureFunctionAdapter(app)
```

An example application can be found [here](https://github.com/erm/azure-functions-python-asgi-example/).

## Dependencies

The base install does not have any hard requirements, but there are dependencies required depending on platform:

`azure-functions` - *required* for Azure Function support. Can be installed using:

```shell
$ pip3 install mangum[azure]
```
