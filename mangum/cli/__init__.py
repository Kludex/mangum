import logging
import click

from mangum.platforms.aws.commands import aws


logger = logging.getLogger("mangum.cli")


@click.group()
def mangum() -> None:
    pass


mangum.add_command(aws)
