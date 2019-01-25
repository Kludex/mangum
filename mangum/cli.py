import os
import uuid
import subprocess
import shlex
import json
import boto3
import click
from pip._internal import main as pipmain


def get_settings() -> dict:
    cwd = os.getcwd()
    with open(os.path.join(cwd, "settings.json"), "r") as f:
        json_data = f.read()
        settings = json.loads(json_data)
    return settings


def get_endpoints(stack_name: str, resource_name: str) -> str:

    describe_command = (
        "aws cloudformation describe-stacks "
        f"--stack-name {stack_name} "
        "--query 'Stacks[].Outputs'"
    )
    describe_cmd = shlex.split(describe_command)
    res = subprocess.run(describe_cmd, stdout=subprocess.PIPE)
    data = json.loads(res.stdout)
    for i in data:
        for j in i:
            if j["OutputKey"] == f"{resource_name}Api":
                endpoint = j["OutputValue"]
    return f"{endpoint}Prod", f"{endpoint}Stage"


def get_template(
    project_name: str,
    *,
    description: str,
    runtime_version: str,
    resource_name: str,
    root_path: str,
    s3_bucket_uri: str,
) -> str:
    return f"""AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Description: >
    {project_name}

    {description}

Globals:
    Function:
        Timeout: 5

Resources:
    {resource_name}Function:

        Type: AWS::Serverless::Function
        Properties:
            CodeUri: .
            Handler: app.lambda_handler
            Runtime: python{runtime_version}
            # Environment:
            #     Variables:
            #         PARAM1: VALUE
            Events:
                {resource_name}:
                    Type: Api
                    Properties:
                        Path: {root_path}
                        Method: get

Outputs:
    {resource_name}Api:
      Description: "API Gateway endpoint URL for {resource_name} function"
      Value: !Sub "https://${{ServerlessRestApi}}.execute-api.${{AWS::Region}}.amazonaws.com{root_path}"

    {resource_name}Function:
      Description: "{resource_name} Lambda Function ARN"
      Value: !GetAtt {resource_name}Function.Arn

    {resource_name}FunctionIamRole:
      Description: "Implicit IAM Role created for {resource_name} function"
      Value: !GetAtt {resource_name}FunctionRole.Arn
    """


def get_app_template() -> str:
    return f"""from mangum.handlers.aws import aws_handler\n\n
class App:
    def __init__(self, scope) -> None:
        self.scope = scope

    async def __call__(self, receive, send) -> None:
        message = await receive()
        if message["type"] == "http.request":
            await send(
                {{
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }}
            )
            await send({{"type": "http.response.body", "body": b"Hello, world!"}})

def lambda_handler(event, context):
    return aws_handler(App, event, context)

    """


def get_readme_template(
    *, project_name: str, stack_name: str, s3_bucket_name: str
) -> str:
    return f"""# {project_name}

A boilerplate ASGI application for AWS Lambda + API Gateway.

## Deployment

Mangum wraps a few AWS-CLI commands to use the generated settings and template file:

```shell
mangum package
```

Then run to deploy:

```shell
managum deploy
```

You may also run:

```shell
mangum describe
```

to echo the API endpoints to the console.
"""


def get_default_resource_name(project_name: str) -> str:
    if "_" in project_name:
        name_parts = project_name.split("_")
        resource_name = "".join([s.title() for s in name_parts])
    else:
        resource_name = project_name.title()
    return resource_name


@click.group()
def mangum() -> None:
    pass


@mangum.command()
@click.argument("command")
def mangum(command: str) -> None:
    if command == "init":
        click.echo(f"Welcome to Mangum, serverless ASGI!")
        project_name = click.prompt("What is the name of your project?", type=str)
        click.echo(f"{project_name}, great!")
        description = click.prompt(
            "Enter a brief description of your project.",
            type=str,
            default="ASGI application",
        )
        resource_name = click.prompt(
            "What should be the prefix used for naming resources?",
            type=str,
            default=get_default_resource_name(project_name),
        )
        stack_name = resource_name.lower()
        root_path = click.prompt(
            "What should be the root URL path?", type=str, default="/"
        )
        runtime_version = click.prompt(
            "What version of Python are you using?", type=str, default="3.7"
        )

        session = boto3.session.Session()
        current_region = session.region_name
        region_name = click.prompt(
            "What region should be used?", default=current_region
        )

        s3_bucket_name = f"{resource_name.lower()}-{uuid.uuid4()}"
        s3_bucket_uri = f"s3://bucket/{s3_bucket_name}"
        click.echo("Creating S3 bucket...")
        s3 = boto3.resource("s3")
        s3.create_bucket(
            Bucket=s3_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region_name},
        )

        cwd = os.getcwd()
        root_dir = os.path.join(cwd, project_name)
        template = get_template(
            project_name=project_name,
            description=description,
            runtime_version=runtime_version,
            resource_name=resource_name,
            root_path=root_path,
            s3_bucket_uri=s3_bucket_uri,
        )
        app_template = get_app_template()
        click.echo("Creating your local project...")
        os.mkdir(root_dir)

        with open(os.path.join(root_dir, "template.yaml"), "w") as f:
            f.write(template)
        with open(os.path.join(root_dir, "app.py"), "w") as f:
            f.write(app_template)
        with open(os.path.join(root_dir, "requirements.txt"), "w") as f:
            f.write("mangum")

        readme_template = get_readme_template(
            project_name=project_name,
            s3_bucket_name=s3_bucket_name,
            stack_name=stack_name,
        )

        with open(os.path.join(cwd, "README.md"), "w") as f:
            f.write(readme_template)

        with open(os.path.join(cwd, "settings.json"), "w") as f:
            settings = {
                "project_name": project_name,
                "s3_bucket_name": s3_bucket_name,
                "stack_name": stack_name,
                "resource_name": resource_name,
            }
            json_data = json.dumps(settings)
            f.write(json_data)

        pipmain(["install", "mangum", "-t", root_dir, "--ignore-installed", "-q"])
        click.echo("Your app has been generated!")
        click.echo("Run 'mangum package' to begin packaging for deployment.")

    # TODO: Replace these CLI calls somehow, ran into some issues.
    elif command == "package":

        click.echo("Packaging...")

        settings = get_settings()

        project_name = settings["project_name"]
        s3_bucket_name = settings["s3_bucket_name"]

        command = (
            "aws cloudformation package "
            f"--template-file {project_name}/template.yaml "
            f"--output-template-file {project_name}/packaged.yaml "
            f"--s3-bucket {s3_bucket_name}"
        )
        package_cmd = shlex.split(command)
        res = subprocess.run(package_cmd, stdout=subprocess.PIPE)
        if res.returncode != 0:
            click.echo("There was an error...")
        else:
            click.echo("Successfully packaged. Run 'mangum deploy' to deploy it now.")

    elif command == "deploy":

        click.echo("Deploying! This may take some time...")
        settings = get_settings()
        project_name = settings["project_name"]
        stack_name = settings["stack_name"]
        resource_name = settings["resource_name"]

        command = (
            "aws cloudformation deploy "
            f"--template-file {project_name}/packaged.yaml "
            f"--stack-name {stack_name} "
            "--capabilities CAPABILITY_IAM"
        )
        deploy_cmd = shlex.split(command)
        res = subprocess.run(deploy_cmd, stdout=subprocess.PIPE)
        if res.returncode != 0:
            click.echo("There was an error...")
        else:
            prod, stage = get_endpoints(stack_name, resource_name)
            click.echo(f"API endpoints available at:")
            click.echo(f"* {prod}")
            click.echo(f"* {stage}")

    elif command == "describe":

        settings = get_settings()
        stack_name = settings["stack_name"]
        resource_name = settings["resource_name"]
        prod, stage = get_endpoints(stack_name, resource_name)
        click.echo(f"API endpoints available at:")
        click.echo(f"* {prod}")
        click.echo(f"* {stage}")


cli = click.CommandCollection(sources=[mangum])


def main() -> None:
    mangum()


if __name__ == "__main__":
    main()
