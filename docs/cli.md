# Mangum CLI (experimental)

Mangum provides a command-line interface for creating a deployment configuration and build, however the adapter class may be used standalone in any custom deployment.

**Note**: This is a heavy work-in-progress, and it may be removed/changed at any point.

## Requirements

- Local AWS Credentials
- [AWS CLI](https://aws.amazon.com/cli/)

## Installation

There are two required dependencies for using the CLI, `boto3` and `click`, they can be installed with Mangum using this command:

```shell
pip install mangum[full]
```

## Commands

`mangum init` - Create a new deployment configuration.

`mangum build` - Create a local build.

`mangum deploy` - Deploy the packaged project.

`mangum package` -  Package the local build.

`mangum describe` -  Retrieve the endpoints for the deployment.

`mangum validate` - Validate the AWS CloudFormation template.

## Tutorial

The steps below outline a basic [FastAPI](https://fastapi.tiangolo.com/) deployment, however you should be able to use any ASGI framework/application with the adapter.

### Step 1 - Create a local project

First, create a new directory `app/`, this is the folder that will contain the main application code and function handler.

Then create a file `asgi.py` with the following:

```python
from mangum import Mangum
from fastapi import FastAPI


app = FastAPI()


@app.post("/items/")
def create_item(item_id: int):
    return {"id": item_id}


@app.get("/items/")
def list_items():
    items = [{"id": i} for i in range(10)]
    return items


@app.get("/")
def read_root():
    return {"Hello": "World!"}


handler = Mangum(app)

```

This demonstrates a basic FastAPI application, the most relevant part is:

```python
handler = Mangum(app)
```

The `handler` variable will be used as the handler name defined in the CloudFormation template to be generated later.

Lastly, create a `requirements.txt` file to include Mangum and FastAPI in the build:

```
mangum
fastapi
```


### Step 2 - Create a new deployment configuration
    
Run the following command with a name for the project (required) and optionally include the name of an S3 bucket and the region (these values can be changed later):

```shell
mangum init <name> [bucket-name] [region-name]
```

After defining the configuration a `mangum.yml` file will be generated, the current directory should now look this:

```shell

├── app
│   └── asgi.py
├── mangum.yml
└── requirements.txt
```

### Step 3 - Create a local build

Run the following command to create a local application build:

```shell
mangum build
```

This will create a `build/` directory containing the application code and any dependencies included in `requirements.txt`.

### Step 4 - Package the local build

Run the following command to package the local build:

```shell
mangum package
```

This wraps the AWS CLI's `package` command, it uses the definitions in `mangum.yml` to produce a `packaged.yml` file and a `template.yml` file.

### Step 5 - Deploy the packaged build

Run the following command to deploy the packaged build:

```shell
mangum deploy
```

This wraps the AWS CLI's `deploy` command. It may take a few minutes to complete. If successful, the endpoints for the deployed application will be displayed in the console.
