import uuid  # pragma: no cover
import click  # pragma: no cover
import boto3  # pragma: no cover
from mangum.cli.aws_cli import aws_deploy, aws_describe, aws_package  # pragma: no cover
from mangum.cli.helpers import (  # pragma: no cover
    get_settings,
    get_default_resource_name,
    build_project,
    get_log_events,
)


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
        root_path = click.prompt(
            "What should be the root URL path?", type=str, default="/"
        )
        runtime_version = click.prompt(
            "What version of Python are you using?", type=str, default="3.7"
        )
        timeout = click.prompt(
            "What should the timeout be (in seconds, max=300)?", type=int, default=300
        )

        # Retrieve the default region name.
        session = boto3.session.Session()
        current_region = session.region_name
        region_name = click.prompt(
            "What region should be used?", default=current_region
        )

        s3_bucket_name = f"{resource_name.lower()}-{uuid.uuid4()}"

        # Generate an S3 bucket for the project or use an existing one.
        existing_s3_bucket_name = click.prompt(
            "An S3 bucket is required. \n\nEnter the name of an existing bucket, or "
            f"one will be generated at:\n\ns3://bucket/{s3_bucket_name}",
            type=str,
            default="",
        )
        if not existing_s3_bucket_name:
            click.echo("Creating S3 bucket...")
            s3 = boto3.resource("s3")
            s3.create_bucket(
                Bucket=s3_bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region_name},
            )
        else:
            s3_bucket_name = existing_s3_bucket_name

        # Build the app settings and templates.
        settings = {
            "project_name": project_name,
            "description": description,
            "s3_bucket_name": s3_bucket_name,
            "stack_name": resource_name.lower(),
            "resource_name": resource_name,
            "root_path": root_path,
            "runtime_version": runtime_version,
            "region_name": region_name,
            "timeout": timeout,
        }

        click.echo("Creating your local project...")
        build_project(settings)
        click.echo("Your app has been generated!")
        click.echo("Run 'mangum package' to begin packaging for deployment.")

    elif command == "package":
        click.echo("Packaging your application...")
        settings = get_settings()
        packaged = aws_package(settings)
        if not packaged:
            click.echo("There was an error...")
        else:
            click.echo("Successfully packaged. Run 'mangum deploy' to deploy it now.")

    elif command == "deploy":
        click.echo("Deploying! This may take some time...")
        settings = get_settings()
        deployed = aws_deploy(settings)
        if not deployed:
            click.echo("There was an error...")
        else:
            prod, stage = aws_describe(settings)
            click.echo(f"Deployment successful! API endpoints available at:")
            click.echo(f"* {prod}")
            click.echo(f"* {stage}")

    elif command == "describe":
        settings = get_settings()
        prod, stage = aws_describe(settings)
        click.echo(f"API endpoints available at:")
        click.echo(f"* {prod}")
        click.echo(f"* {stage}")

    elif command == "tail":
        settings = get_settings()
        # Display the CloudWatch logs for the last 10 minutes.
        # TODO: Make this configurable.
        log_events = get_log_events(
            f"/aws/lambda/{settings['resource_name']}Function", minutes=10
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
