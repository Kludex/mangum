# How to deploy an ASGI app to AWS Lambda & API Gateway

This guide will explain how to generate a basic AWS Lambda deployment configuration suitable for [ASGI](https://asgi.readthedocs.io/en/latest/) applications. Mangum includes tools to assist with generating [AWS SAM (Serverless Application Model)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) templates and handling packaging/deployment. 

**Note**: The AWS configuration generation methods are currently experimental (may change).

## Requirements

- Python 3.6+
- [AWS-CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
- AWS credentials

### Step 1 - Setup and configuration

First, install Mangum with all the optional dependencies (needed for AWS):

```shell
$ pip3 install mangum[aws]
```


Begin the process of generating a project. You should initiate this in a directory above your application:

```shell
$ mangum init
```

After answering a series of questions, a few boilerplate configuration files will be generated in the current directory:

* `settings.json`

The file with all the AWS resource details, needed to inform the AWS CLI wrapper methods with the correct parameters. This should not be modified directly.

* `template.yaml`

The AWS SAM template used to define the resources/stack. This may be modified as needed to specify additional configuration according to the SAM spec.

* `requirements.txt`

All that Python packages that should be installed in the build directory. It contains only `mangum` by default as it is the only requirement for the ASGI adapter.

* `asgi.py`

This is the module that is specified in the generated SAM template. It contains the following:

```python
from mangum.platforms.aws.middleware import AWSLambdaMiddleware
from YourApp.app import app


handler = AWSLambdaMiddleware(app)  # optionally set debug=True
```

You will need to modify the `asgi.py` file to import your application to be run by the middleware. Alternatively, you may update the `template.yaml` to point directly to a different handler location - the `asgi.py` is included for convenience.

After generating the configuration, the file structure should look something like this:

```shell
├── YourProject
│   ├── YourApp/
│   ├── asgi.py
│   ├── packaged.yaml
│   ├── requirements.txt
│   ├── settings.json
│   └── template.yaml
```

### Step 2 - Build the application

Next you will be prompted to run:

```shell
$ mangum aws build
```

This will install all the packages listed in `requirements.txt` and copy over your application to the `build/` directory to be packaged.

### Step 3 - Packaging for deployment

Next run the package command to prepare the application build for deployment:

```shell
$ mangum package
```

After the packaging completes, you may then deploy:

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

If you run into any issues, you can lookup the function logs in CloudWatch or enter the following command:

```shell
$ mangum tail
```

This will tail the last 10 minutes of logs activity for the function.
