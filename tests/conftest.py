from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import boto3
import pytest

from mangum.types import LambdaEvent

if TYPE_CHECKING:
    from testcontainers.community.localstack import LocalStackContainer

PROJECT_ROOT = Path(__file__).parent.parent
ECHO_LAMBDA_DIR = Path(__file__).parent / "echo_lambda"


@pytest.fixture
def mock_aws_api_gateway_event(request: pytest.FixtureRequest) -> LambdaEvent:
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    event: dict[str, Any] = {
        "path": "/test/hello",
        "body": body,
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, lzma, sdch, br",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Cookie": "cookie1; cookie2",
            "Host": "test.execute-api.us-west-2.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-For": "192.168.100.1, 192.168.1.1",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
        },
        "pathParameters": {"proxy": "hello"},
        "requestContext": {
            "accountId": "123456789012",
            "resourceId": "us4z18",
            "stage": "Prod",
            "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
            "identity": {
                "cognitoIdentityPoolId": "",
                "accountId": "",
                "cognitoIdentityId": "",
                "caller": "",
                "apiKey": "",
                "sourceIp": "192.168.100.1",
                "cognitoAuthenticationType": "",
                "cognitoAuthenticationProvider": "",
                "userArn": "",
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",  # noqa: E501
                "user": "",
            },
            "resourcePath": "/{proxy+}",
            "httpMethod": method,
            "apiId": "123",
        },
        "resource": "/{proxy+}",
        "httpMethod": method,
        "queryStringParameters": (
            {k: v[0] for k, v in multi_value_query_parameters.items()} if multi_value_query_parameters else None
        ),
        "multiValueQueryStringParameters": multi_value_query_parameters or None,
        "stageVariables": {"stageVarName": "stageVarValue"},
    }
    return event


@pytest.fixture
def mock_http_api_event_v2(request: pytest.FixtureRequest) -> LambdaEvent:
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    query_string = request.param[3]
    event: LambdaEvent = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/my/path",
        "rawQueryString": query_string,
        "cookies": ["cookie1", "cookie2"],
        "headers": {
            "accept-encoding": "gzip,deflate",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
            "host": "test.execute-api.us-west-2.amazonaws.com",
        },
        "queryStringParameters": (
            {k: v[0] for k, v in multi_value_query_parameters.items()} if multi_value_query_parameters else None
        ),
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "authorizer": {
                "jwt": {
                    "claims": {"claim1": "value1", "claim2": "value2"},
                    "scopes": ["scope1", "scope2"],
                }
            },
            "domainName": "id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "id",
            "http": {
                "method": method,
                "path": "/my/path",
                "protocol": "HTTP/1.1",
                "sourceIp": "192.168.100.1",
                "userAgent": "agent",
            },
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390,
        },
        "body": body,
        "pathParameters": {"parameter1": "value1"},
        "isBase64Encoded": False,
        "stageVariables": {"stageVariable1": "value1", "stageVariable2": "value2"},
    }

    return event


@pytest.fixture
def mock_http_api_event_v1(request: pytest.FixtureRequest) -> LambdaEvent:
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    query_string = request.param[3]
    event: LambdaEvent = {
        "version": "1.0",
        "routeKey": "$default",
        "rawPath": "/my/path",
        "path": "/my/path",
        "httpMethod": method,
        "rawQueryString": query_string,
        "cookies": ["cookie1", "cookie2"],
        "headers": {
            "accept-encoding": "gzip,deflate",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
            "host": "test.execute-api.us-west-2.amazonaws.com",
        },
        "queryStringParameters": (
            {k: v[-1] for k, v in multi_value_query_parameters.items()} if multi_value_query_parameters else None
        ),
        "multiValueQueryStringParameters": (
            {k: v for k, v in multi_value_query_parameters.items()} if multi_value_query_parameters else None
        ),
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "authorizer": {
                "jwt": {
                    "claims": {"claim1": "value1", "claim2": "value2"},
                    "scopes": ["scope1", "scope2"],
                }
            },
            "domainName": "id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "id",
            "http": {
                "protocol": "HTTP/1.1",
                "sourceIp": "192.168.100.1",
                "userAgent": "agent",
            },
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390,
        },
        "body": body,
        "pathParameters": {"parameter1": "value1"},
        "isBase64Encoded": False,
        "stageVariables": {"stageVariable1": "value1", "stageVariable2": "value2"},
    }

    return event


def build_lambda_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for source_dir, prefix in [
            (PROJECT_ROOT / "mangum", "mangum"),
            (ECHO_LAMBDA_DIR, ""),
        ]:
            for path in source_dir.rglob("*.py"):
                archive.write(path, f"{prefix}/{path.relative_to(source_dir)}" if prefix else path.name)
        import typing_extensions

        archive.write(typing_extensions.__file__, "typing_extensions.py")
    return buffer.getvalue()


@pytest.fixture(scope="session")
def localstack() -> Iterator[LocalStackContainer]:
    from testcontainers.community.localstack import LocalStackContainer

    with LocalStackContainer("localstack/localstack:4").with_volume_mapping(
        "/var/run/docker.sock", "/var/run/docker.sock", "rw"
    ) as container:
        yield container


@pytest.fixture(scope="session")
def lambda_client(localstack: LocalStackContainer) -> Any:
    return boto3.client(
        "lambda",
        endpoint_url=localstack.get_url(),
        region_name=localstack.region_name,
        aws_access_key_id="testcontainers-localstack",
        aws_secret_access_key="testcontainers-localstack",
    )


@pytest.fixture(scope="session")
def echo_function_arn(lambda_client: Any) -> str:
    lambda_client.create_function(
        FunctionName="mangum-echo",
        Runtime="python3.12",
        Role="arn:aws:iam::000000000000:role/lambda-role",
        Handler="echo_handler.handler",
        Code={"ZipFile": build_lambda_zip()},
        Timeout=30,
    )
    lambda_client.get_waiter("function_active_v2").wait(FunctionName="mangum-echo")
    return str(lambda_client.get_function(FunctionName="mangum-echo")["Configuration"]["FunctionArn"])


@pytest.fixture(scope="session")
def function_url(localstack: LocalStackContainer, lambda_client: Any, echo_function_arn: str) -> str:
    response = lambda_client.create_function_url_config(FunctionName="mangum-echo", AuthType="NONE")
    url = str(response["FunctionUrl"])
    host_port = localstack.get_exposed_port(localstack.edge_port)
    return url.replace(":4566", f":{host_port}")


@pytest.fixture(scope="session")
def rest_api_url(localstack: LocalStackContainer, echo_function_arn: str) -> str:
    apigateway = boto3.client(
        "apigateway",
        endpoint_url=localstack.get_url(),
        region_name=localstack.region_name,
        aws_access_key_id="testcontainers-localstack",
        aws_secret_access_key="testcontainers-localstack",
    )
    rest_api_id = apigateway.create_rest_api(name="mangum-echo")["id"]
    root_id = apigateway.get_resources(restApiId=rest_api_id)["items"][0]["id"]
    proxy_id = apigateway.create_resource(restApiId=rest_api_id, parentId=root_id, pathPart="{proxy+}")["id"]
    for resource_id in (root_id, proxy_id):
        apigateway.put_method(restApiId=rest_api_id, resourceId=resource_id, httpMethod="ANY", authorizationType="NONE")
        apigateway.put_integration(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod="ANY",
            type="AWS_PROXY",
            integrationHttpMethod="POST",
            uri=(
                f"arn:aws:apigateway:{localstack.region_name}:lambda:path/2015-03-31"
                f"/functions/{echo_function_arn}/invocations"
            ),
        )
    apigateway.create_deployment(restApiId=rest_api_id, stageName="test")
    return f"{localstack.get_url()}/restapis/{rest_api_id}/test/_user_request_/"
