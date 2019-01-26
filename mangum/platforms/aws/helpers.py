import datetime
import operator
import boto3


def get_default_region_name() -> str:
    session = boto3.session.Session()
    return session.region_name


def get_default_resource_name(project_name: str) -> str:
    if "_" in project_name:
        name_parts = project_name.split("_")
        resource_name = "".join([s.title() for s in name_parts])
    else:
        resource_name = project_name.title()  # pragma: no cover
    return resource_name


def get_log_events(group_name: str, minutes: int) -> list:  # pragma: no cover
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
