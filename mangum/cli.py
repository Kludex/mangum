import datetime
import operator
import click
import boto3
from mangum.__version__ import __version__


@click.group()
def cli():
    pass


@cli.command()
def version():
    """Display the current version"""
    click.echo(f"Mangum v{__version__}")


def get_log_events(group_name: str, minutes: int) -> list:
    end_dt = datetime.datetime.now()
    start_dt = end_dt - datetime.timedelta(minutes=minutes)
    start_time = int(start_dt.timestamp()) * 1000
    end_time = int(end_dt.timestamp()) * 1000

    kwargs = {
        "logGroupName": group_name,
        "startTime": start_time,
        "endTime": end_time,
        "limit": 10000,
    }

    all_events = []
    client = boto3.client("logs")

    while True:
        res = client.filter_log_events(**kwargs)
        all_events += res["events"]

        try:
            kwargs["nextToken"] = res["nextToken"]
        except KeyError:
            break

    return sorted(all_events, key=operator.itemgetter("timestamp"), reverse=False)


@cli.command()
@click.argument("name")
def tail(name: str, minutes: int = 60) -> None:
    """
    Display the CloudWatch logs for a specified period, defaults to the last hour.
    """
    log_events = get_log_events(f"/aws/lambda/{name}", minutes=minutes)
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


cli = click.CommandCollection(sources=[cli])


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
