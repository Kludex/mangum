# How to deploy an ASGI app to AWS Lambda & API Gateway

This guide will explain how to deploy a basic [ASGI](https://asgi.readthedocs.io/en/latest/) application to AWS Lambda & API Gateway. Mangum includes tools to assist with generating an example ASGI application using a [AWS SAM (Serverless Application Model)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) template.

**Note**: These commands-much like most of the project currently-are being actively developed and may be buggy.

## Requirements

- Python 3.6+
- [AWS-CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
- AWS credentials

### Step 1 - Setup and configuration

First, install Mangum with all the optional dependencies (needed for AWS):

```shell
$ pip3 install mangum[full]
```


Begin the process of generating a project:

```shell
$ mangum init
```

After answering a series of questions, the following will be generated in the current directory:

* A boilerplate ASGI app with the latest version of `mangum` installed from PyPi for deployment to AWS.
    
* A `settings.json` file with the generated AWS resource information.

* An S3 bucket to be used with the app.

* A `template.yaml` containing the AWS SAM template.

Once the initial configuration step is complete, you should have an app structure that looks like this:

```shell
├── README.md
├── my_project
│   ├── app.py
│   ├── mangum/
│   ├── requirements.txt
│   └── template.yaml
└── settings.json
```

### Step 2 - Packaging and deployment

You will then be prompted to enter the following commands, these are simply wrappers around the AWS-CLI commands using the `settings.json` values generated previously as arguments.

```shell
$ mangum package
```

After packaging, you then can deploy:

```shell
$ mangum deploy
```

**Note**: This may take awhile.

If the deployment is successful, then the API endpoints for the stages will be displayed:

```shell
Deployment successful! API endpoints available at:
* https://xxxxx.execute-api.ap-southeast-1.amazonaws.com/Prod
* https://xxxxx.execute-api.ap-southeast-1.amazonaws.com/Stage
```

Visiting the endpoint should then produce a simple "Hello World" response. If you run into any issues, you can lookup the function logs in CloudWatch or enter the following command:

```shell
$ mangum tail
```

This will tail the last 10 minutes of logs activity for the function.

### Using ASGI frameworks

The generated "hello world" application is a raw example, but you can easily use any ASGI framework with the adapter. For example, you could replace the content of the `app.py` generated previously with a Starlette application to achieve a similar result:

```python
from mangum.adapters.aws import run_asgi

from starlette.applications import Starlette
from starlette.responses import JSONResponse

app = Starlette()


@app.route("/")
async def homepage(request):
    return JSONResponse({"hello": "world"})


def lambda_handler(event, context):
    return run_asgi(app, event, context)
```

You would also have to include Starlette as a dependency in the package:

```
$ pip3 install . -t starlette
```

And re-run the `mangum package` and `mangum deploy` commands to update the function.

### Additional considerations

The application generation and deployment tools included in Mangum are mainly intended to quickly produce and deploy a very basic boilerplate application.

**Keep in mind:**

* As of this writing, only simple application examples have been tested with the adapters (work-in-progress).

* AWS SAM templates are only means of handling the deployment and configuration, it was chosen here because it offered the path of least resistance to getting an app generated and deployed with all the necessary permissions/resources/roles/etc. included.

* You will need to manually edit the generated AWS SAM template to extend the functionality of the stack and leverage additional AWS services.

At some point it would be nice to improve the CLI tool to be more comprehensive with some validation/safety features and possibly a way to eliminate the AWS-CLI as a requirement for deployment/packaging. 

There is an open issue for doing so [here](https://github.com/erm/mangum/issues/10).
