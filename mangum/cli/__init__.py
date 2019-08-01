import os
import uuid

import yaml
from botocore.exceptions import ClientError
import boto3
import click


from mangum.cli.config import Config


@click.group()
def mangum() -> None:
    pass


def get_config() -> Config:
    config_dir = os.getcwd()
    config_file_path = os.path.join(config_dir, "mangum.yml")
    if not os.path.exists(config_file_path):
        raise IOError(f"File not found: '{config_file_path}' does not exist.")
    with open(config_file_path, "r") as f:
        config_data = f.read()
    try:
        config_data = yaml.safe_load(config_data)
    except yaml.YAMLError as exc:
        raise RuntimeError(exc)
    config = Config(**config_data)
    return config


def get_default_region_name() -> str:  # pragma: no cover
    session = boto3.session.Session()
    return session.region_name


@mangum.command()
@click.argument("name", required=True)
@click.argument("bucket_name", required=False)
@click.argument("region_name", required=False)
def init(name: str, bucket_name: str = None, region_name: str = None) -> None:
    """
    Create a new deployment configuration.

    Required arguments:

        - name
            Specify a name for the project. This will be used as a prefix when naming
            and identifying resources.

    Optional arguments:

        - bucket_name
            Specify an S3 bucket name to contain the application build.

        - region_name
            Specify the region to use for the deployment.

    """
    click.echo("Generating initial configuration...")
    config_dir = os.getcwd()
    config = {
        "name": name,
        "code_dir": "app",
        "handler": "asgi.handler",
        "bucket_name": bucket_name,
        "region_name": region_name,
        "timeout": 300,
    }
    with open(os.path.join(config_dir, "mangum.yml"), "w") as f:
        config_data = yaml.dump(config, default_flow_style=False, sort_keys=False)
        f.write(config_data)
    with open(os.path.join(config_dir, "requirements.txt"), "w") as f:
        f.write("mangum\n")
    click.echo(f"Configuration saved to: {config_dir}")


@mangum.command()
@click.option("--no-pip", default=False, is_flag=True)
def build(no_pip: bool = False) -> None:
    """
    Create a local build.

    Optional arguments:

        - no_pip
            Update only the application code, ignore requirements.

    """
    config = get_config()
    config.build(no_pip=no_pip)
    click.echo("Build complete!")


@mangum.command()
@click.argument("bucket_name", required=False)
@click.argument("region_name", required=False)
def create_bucket(bucket_name: str, region_name: str) -> None:
    """
    Create a new S3 bucket.
    """

    s3_client = boto3.client("s3")

    if not bucket_name:  # pragma: no cover
        click.echo("No bucket name provided, one will be generated.")
        bucket_name = f"mangum-{uuid.uuid4()}"

    if not region_name:  # pragma: no cover
        region_name = get_default_region_name()
        click.echo(f"No region specified, using default.")

    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region_name},
        )
    except ClientError as exc:
        click.echo(exc)
    else:
        click.echo(f"Bucket name:\n{bucket_name}\nRegion name:\n{region_name}")


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
