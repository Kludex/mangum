import os
import json
import operator
import datetime
import boto3


def get_settings() -> dict:  # pragma: no cover
    cwd = os.getcwd()
    with open(os.path.join(cwd, "settings.json"), "r") as f:
        json_data = f.read()
        settings = json.loads(json_data)
    return settings


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


def get_sam_template(settings: dict) -> str:
    return f"""AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Description: >
    {settings['project_name']}

    {settings['description']}

Globals:
    Function:
        Timeout: {settings['timeout']}

Resources:
    {settings['resource_name']}Function:

        Type: AWS::Serverless::Function
        Properties:
            FunctionName: {settings['resource_name']}Function
            CodeUri: .
            Handler: app.lambda_handler
            Runtime: python{settings['runtime_version']}
            # Environment:
            #     Variables:
            #         PARAM1: VALUE
            Events:
                {settings['resource_name']}:
                    Type: Api
                    Properties:
                        Path: {settings['root_path']}
                        Method: get

Outputs:
    {settings['resource_name']}Api:
      Description: "API Gateway endpoint URL for {settings['resource_name']} function"
      Value: !Sub "https://${{ServerlessRestApi}}.execute-api.${{AWS::Region}}.amazonaws.com{settings['root_path']}"

    {settings['resource_name']}Function:
      Description: "{settings['resource_name']} Lambda Function ARN"
      Value: !GetAtt {settings['resource_name']}Function.Arn

    {settings['resource_name']}FunctionIamRole:
      Description: "Implicit IAM Role created for {settings['resource_name']} function"
      Value: !GetAtt {settings['resource_name']}FunctionRole.Arn
    """


def get_app_template() -> str:
    return f"""from mangum.adapters.aws import run_asgi


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
    return run_asgi(App, event, context)

    """


def get_readme_template(settings: dict) -> str:
    return f"""# {settings['project_name']}

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
        resource_name = project_name.title()  # pragma: no cover
    return resource_name


def build_project(settings: dict) -> None:  # pragma: no cover
    from pip._internal import main as pipmain

    CURRENT_DIR = os.getcwd()
    PROJECT_DIR = os.path.join(CURRENT_DIR, settings["project_name"])
    os.mkdir(PROJECT_DIR)

    SAM_TEMPLATE = get_sam_template(settings)
    APP_TEMPLATE = get_app_template()
    README_TEMPLATE = get_readme_template(settings)

    with open(os.path.join(PROJECT_DIR, "template.yaml"), "w") as f:
        f.write(SAM_TEMPLATE)

    with open(os.path.join(PROJECT_DIR, "app.py"), "w") as f:
        f.write(APP_TEMPLATE)

    with open(os.path.join(PROJECT_DIR, "requirements.txt"), "w") as f:
        f.write("mangum")

    with open(os.path.join(CURRENT_DIR, "README.md"), "w") as f:
        f.write(README_TEMPLATE)

    with open(os.path.join(CURRENT_DIR, "settings.json"), "w") as f:
        json_data = json.dumps(settings)
        f.write(json_data)

    pipmain(["install", "mangum", "-t", PROJECT_DIR, "--ignore-installed", "-q"])
