import click  # pragma: no cover
import boto3  # pragma: no cover
import os

from mangum.platforms.aws.helpers import (
    get_default_resource_name,
    get_default_region_name,
)
from mangum.platforms.aws.config import AWSConfig


@click.group()  # pragma: no cover
def mangum() -> None:
    pass


@mangum.command()  # pragma: no cover
@click.argument("command")  # pragma: no cover
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
        url_root = click.prompt(
            "What should be the root URL path?", type=str, default="/"
        )
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
        config_dir = os.getcwd()
        package_dir = os.path.join(config_dir, project_name)
        config = AWSConfig(
            config_dir=config_dir,
            package_dir=package_dir,
            project_name=project_name,
            description=description,
            s3_bucket_name=s3_bucket_name,
            resource_name=resource_name,
            stack_name=resource_name.lower(),
            url_root=url_root,
            runtime_version=runtime_version,
            region_name=region_name,
            timeout=timeout,
            generate_s3=generate_s3,
        )
        click.echo("Creating your local project...")
        config.build()
        click.echo(
            "Your app has been generated!\n"
            "Run 'mangum package' to begin packaging for deployment."
        )

    elif command == "package":
        click.echo("Packaging your application...")
        packaged = AWSConfig.get_config_from_file().cli_package()
        if not packaged:
            click.echo("There was an error...")
        else:
            click.echo("Successfully packaged. Run 'mangum deploy' to deploy it now.")

    elif command == "deploy":
        click.echo("Deploying! This may take some time...")
        deployed = AWSConfig.get_config_from_file().cli_deploy()
        if not deployed:
            click.echo("There was an error...")
        else:
            endpoints = AWSConfig.get_config_from_file().cli_describe()
            click.echo(
                f"Deployment successful! API endpoints available at:\n\n{endpoints}"
            )

    elif command == "describe":
        endpoints = AWSConfig.get_config_from_file().cli_describe()
        if not endpoints:
            click.echo("Error! Could not retrieve endpoints.")
        else:
            click.echo(f"API endpoints available at:\n\n{endpoints}")

    elif command == "rebuild":
        click.echo("Re-building the local app files.")
        AWSConfig.get_config_from_file().rebuild()
    # elif command == "tail":
    #     settings = get_settings()
    #     # Display the CloudWatch logs for the last 10 minutes.
    #     # TODO: Make this configurable.
    #     log_events = get_log_events(
    #         f"/aws/lambda/{settings['resource_name']}Function", minutes=10
    #     )
    #     log_output = []
    #     for log in log_events:
    #         message = log["message"].rstrip()
    #         if not any(
    #             i in message
    #             for i in ("START RequestId", "REPORT RequestId", "END RequestId")
    #         ):
    #             timestamp = log["timestamp"]
    #             s = f"[{timestamp}] {message}"
    #             log_output.append(s)

    #     click.echo("\n".join(log_output))
