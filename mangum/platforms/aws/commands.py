import click
import uuid
import boto3
import os
from mangum.platforms.aws.helpers import (
    get_default_resource_name,
    get_default_region_name,
    get_log_events,
    get_config,
)
from mangum.platforms.aws.config import AWSConfig


class AWSGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail("Too many matches: %s" % ", ".join(sorted(matches)))


@click.command(cls=AWSGroup)
def aws() -> None:
    pass


@aws.command()
def init() -> None:
    click.echo(f"Welcome to Mangum, serverless ASGI!")
    project_name = click.prompt("What is the name of the project?", type=str)
    click.echo(f"{project_name}, great!")
    project_dir_name = click.prompt(
        "What is the name of the directory that contains the project code?", type=str
    )
    config_dir = os.getcwd()
    project_dir = os.path.join(config_dir, project_dir_name)
    if not os.path.isdir(project_dir):
        raise click.ClickException(
            f"Directory not found at {project_dir}! "
            "(Hint: The project folder must be in current working directory.)"
        )
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
    url_root = click.prompt("What should be the root URL path?", type=str, default="/")
    runtime_version = click.prompt(
        "What version of Python are you using?", type=str, default="3.7"
    )
    timeout = click.prompt(
        "What should the timeout be (in seconds, max=300)?", type=int, default=300
    )
    default_region_name = get_default_region_name()
    region_name = click.prompt(
        "What region should be used?", default=default_region_name
    )
    s3_bucket_name = click.prompt(
        "An S3 bucket is required. \n\nEnter the name of an existing bucket or "
        f"one will be generated.",
        type=str,
        default="",
    )
    generate_s3 = s3_bucket_name == ""
    if generate_s3:
        s3_bucket_name = f"{resource_name.lower()}-{uuid.uuid4()}"
        s3 = boto3.resource("s3")
        s3.create_bucket(
            Bucket=s3_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region_name},
        )

    config = AWSConfig(
        project_name=project_name,
        description=description,
        s3_bucket_name=s3_bucket_name,
        resource_name=resource_name,
        url_root=url_root,
        runtime_version=runtime_version,
        region_name=region_name,
        timeout=timeout,
        stack_name=resource_name.lower(),
    )
    click.echo("Creating your local project...")
    config.init()
    click.echo(
        "Your app configuration has been generated!\n"
        "Modify the 'template.yaml' or 'requirements.txt' if you need to, otherwise "
        "run 'mangum aws build' to prepare the local project for packaging."
    )


@aws.command()
def build() -> None:
    """
    Install the packages listed in the requirements file and copy the application files
    to the 'build/' directory to prepare for packaging.
    """
    config, error = get_config()
    if error is not None:
        click.echo(error)
    else:
        click.echo("Building application and installing requirements...")
        config.build()
        click.echo("Build complete!")


@aws.command()
def package() -> None:
    config, error = get_config()
    if error is not None:
        click.echo(error)
    else:
        click.echo("Packaging your application...")
        packaged = config.cli_package()
        if not packaged:
            click.echo("There was an error...")
        else:
            click.echo(
                "Successfully packaged. Run 'mangum aws deploy' to deploy it now."
            )


@aws.command()
def deploy() -> None:
    config, error = get_config()
    if error is not None:
        click.echo(error)
    else:
        click.echo("Deploying your application! This may take some time...")
        deployed = config.cli_deploy()
        if not deployed:
            click.echo("There was an error...")
        else:
            endpoints = config.cli_describe()
            click.echo(
                f"Deployment successful! API endpoints available at:\n\n{endpoints}"
            )


@aws.command()
def describe() -> None:
    config, error = get_config()
    if error is not None:
        click.echo(error)
    else:
        endpoints = config.cli_describe()
        if not endpoints:
            click.echo("Error! Could not retrieve endpoints.")
        else:
            click.echo(f"API endpoints available at:\n\n{endpoints}")


@aws.command()
def validate() -> None:
    config, error = get_config()
    if error is not None:
        click.echo(error)
    else:
        error = config.validate()
        if not error:
            click.echo("Template file validated successfully!")
        else:
            click.echo(error)


@aws.command()
def tail() -> None:
    config, error = get_config()
    if error is not None:
        click.echo(error)
    else:
        # Display the CloudWatch logs for the last 10 minutes.
        # TODO: Make this configurable.
        log_events = get_log_events(
            f"/aws/lambda/{config.resource_name}Function", minutes=10
        )
        log_output = []
        for log in log_events:
            message = log["message"].rstrip()
            if not any(
                i in message
                for i in ("START RequestId", "REPORT RequestId", "END RequestId")
            ):
                timestamp = log["timestamp"]
                s = f"[{timestamp}] {message}"
                log_output.append(s)

        click.echo("\n".join(log_output))
