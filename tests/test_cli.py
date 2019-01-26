from mangum.cli.helpers import (
    get_default_resource_name,
    get_sam_template,
    get_app_template,
    get_readme_template,
)


TEST_SETTINGS = {
    "project_name": "hello_asgi",
    "description": "An ASGI application",
    "runtime_version": "3.7",
    "root_path": "/",
    "s3_bucket_name": "helloasgi-xxxxx",
    "stack_name": "helloasgi",
    "resource_name": "HelloAsgi",
}


def test_get_default_resource_name() -> None:
    project_name = "hello_world_project"
    resource_name = get_default_resource_name(project_name)
    assert resource_name == "HelloWorldProject"


def test_get_sam_template() -> None:

    template = get_sam_template(TEST_SETTINGS)
    assert (
        template.strip()
        == """AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Description: >
    hello_asgi

    An ASGI application

Globals:
    Function:
        Timeout: 5

Resources:
    HelloAsgiFunction:

        Type: AWS::Serverless::Function
        Properties:
            CodeUri: .
            Handler: app.lambda_handler
            Runtime: python3.7
            # Environment:
            #     Variables:
            #         PARAM1: VALUE
            Events:
                HelloAsgi:
                    Type: Api
                    Properties:
                        Path: /
                        Method: get

Outputs:
    HelloAsgiApi:
      Description: "API Gateway endpoint URL for HelloAsgi function"
      Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/"

    HelloAsgiFunction:
      Description: "HelloAsgi Lambda Function ARN"
      Value: !GetAtt HelloAsgiFunction.Arn

    HelloAsgiFunctionIamRole:
      Description: "Implicit IAM Role created for HelloAsgi function"
      Value: !GetAtt HelloAsgiFunctionRole.Arn""".strip()
    )


def test_get_app_template() -> None:
    template = get_app_template()
    assert (
        template.strip()
        == """from mangum.adapters.aws import run_asgi


class App:
    def __init__(self, scope) -> None:
        self.scope = scope

    async def __call__(self, receive, send) -> None:
        message = await receive()
        if message["type"] == "http.request":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello, world!"})

def lambda_handler(event, context):
    return run_asgi(App, event, context)

    """.strip()
    )


def test_get_readme_template() -> None:
    template = get_readme_template(TEST_SETTINGS)
    assert (
        template.strip()
        == f"""# {TEST_SETTINGS['project_name']}

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
""".strip()
    )
