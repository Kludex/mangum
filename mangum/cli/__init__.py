import click

from mangum.platforms.aws.commands import aws


@click.group()
def mangum() -> None:
    pass


mangum.add_command(aws)
