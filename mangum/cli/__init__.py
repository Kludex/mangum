import os
import subprocess
import json
import sys
import shutil
import uuid
from dataclasses import dataclass
from typing import Union, Tuple

from mangum.cli.config import MangumConfig


import boto3
import click


@click.group()
def mangum() -> None:
    pass


def get_config() -> MangumConfig:
    config_dir = os.getcwd()
    config_file_path = os.path.join(config_dir, "config.json")
    if not os.path.exists(config_file_path):
        raise IOError(f"File not found: '{config_file_path}' does not exist.")
    with open(config_file_path, "r") as f:
        content = f.read()
    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError:
        raise ValueError(
            f"Invalid JSON data: '{config_file_path}' could not be decoded."
        )

    config = MangumConfig(**content)
    return config


def get_default_region_name() -> str:  # pragma: no cover
    session = boto3.session.Session()
    return session.region_name


@mangum.command()
def init() -> None:
    """
    Create a new deployment configuration.
    """
    config_dir = os.getcwd()
    project_dir = click.prompt(
        "Enter the name of the directory containing the project code"
    )
    project_name = click.prompt("Enter a name for the project", type=str)
    resource_name = project_name.title()
    click.echo(
        f"Creating new configuration in {config_dir} for project {project_name}!"
    )
    handler_name = click.prompt(
        "Enter the name of the handler method", type=str, default="asgi.handler"
    )
    description = click.prompt(
        "Enter a description for the project", type=str, default="ASGI application"
    )
    url_root = click.prompt("Enter the root URL path", type=str, default="/")
    timeout = click.prompt(
        "Enter the function timeout (in seconds, max=300)", type=int, default=300
    )
    default_region_name = get_default_region_name()
    region_name = click.prompt("Enter the region", default=default_region_name)
    s3_bucket_name = click.prompt(
        "Enter the name of an existing bucket or one will be generated.",
        type=str,
        default="",
    )
    if s3_bucket_name == "":
        s3_bucket_name = f"{resource_name.lower()}-{uuid.uuid4()}"
        s3 = boto3.resource("s3")
        res = s3.create_bucket(
            Bucket=s3_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region_name},
        )
        print(res)

    config = MangumConfig(
        config_dir=config_dir,
        project_dir=project_dir,
        project_name=project_name,
        resource_name=resource_name,
        handler_name=handler_name,
        description=description,
        s3_bucket_name=s3_bucket_name,
        url_root=url_root,
        region_name=region_name,
        timeout=timeout,
    )
    click.echo("Creating your local project...")
    config.init()
    click.echo("Done")


@mangum.command()
def build() -> None:
    """
    Create a local build.
    """
    config = get_config()
    config.build()
    click.echo("Build complete!")


@mangum.command()
def package() -> None:
    """
    Package the local build.
    """
    config = get_config()
    click.echo("Packaging your application...")
    res = config.package()
    if not res:
        click.echo("There was an error...")
    else:
        click.echo("Successfully packaged. Run 'mangum deploy' to deploy it now.")


@mangum.command()
def deploy() -> None:
    """
    Deploy the packaged project.
    """
    config = get_config()
    click.echo("Deploying your application! This may take some time...")
    deployed = config.deploy()
    if not deployed:
        click.echo("There was an error...")
    else:
        endpoints = config.describe()
        click.echo(f"Deployment successful! API endpoints available at:\n\n{endpoints}")


@mangum.command()
def validate() -> None:
    """
    Validate the AWS CloudFormation template.
    """
    config = get_config()
    res = config.validate()
    if res is not None:
        click.echo(f"Template Error: {res}")
    else:
        click.echo("Template is valid!")


@mangum.command()
def describe() -> None:
    """
    Retrieve the endpoints for the deployment.
    """
    config = get_config()
    endpoints = config.describe()
    if not endpoints:
        click.echo("Error! Could not retrieve endpoints.")
    else:
        click.echo(f"API endpoints available at:\n\n{endpoints}")


# @mangum.command()
# def tail() -> None:
#     config, error = get_config()
#     if error is not None:
#         click.echo(error)
#     else:
#         # Display the CloudWatch logs for the last 10 minutes.
#         # TODO: Make this configurable.
#         log_events = get_log_events(
#             f"/aws/lambda/{config.resource_name}Function", minutes=10
#         )
#         log_output = []
#         for log in log_events:
#             message = log["message"].rstrip()
#             if not any(
#                 i in message
#                 for i in ("START RequestId", "REPORT RequestId", "END RequestId")
#             ):
#                 timestamp = log["timestamp"]
#                 s = f"[{timestamp}] {message}"
#                 log_output.append(s)

#         click.echo("\n".join(log_output))
