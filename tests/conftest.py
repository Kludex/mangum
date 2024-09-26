import os

import pytest


@pytest.fixture
def mock_aws_api_gateway_event(request):
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    event = {
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
def mock_http_api_event_v2(request):
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    query_string = request.param[3]
    event = {
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
def mock_http_api_event_v1(request):
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    query_string = request.param[3]
    event = {
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


@pytest.fixture
def mock_lambda_at_edge_event(request):
    method = request.param[0]
    path = request.param[1]
    query_string = request.param[2]
    body = request.param[3]

    headers_raw = {
        "accept-encoding": "gzip,deflate",
        "x-forwarded-port": "443",
        "x-forwarded-for": "192.168.100.1",
        "x-forwarded-proto": "https",
        "host": "test.execute-api.us-west-2.amazonaws.com",
    }
    headers = {}
    for key, value in headers_raw.items():
        headers[key.lower()] = [{"key": key, "value": value}]

    event = {
        "Records": [
            {
                "cf": {
                    "config": {
                        "distributionDomainName": "mock-distribution.local.localhost",
                        "distributionId": "ABC123DEF456G",
                        "eventType": "origin-request",
                        "requestId": "lBEBo2N0JKYUP2JXwn_4am2xAXB2GzcL2FlwXI8G59PA8wghF2ImFQ==",
                    },
                    "request": {
                        "clientIp": "192.168.100.1",
                        "headers": headers,
                        "method": method,
                        "origin": {
                            "custom": {
                                "customHeaders": {
                                    "x-lae-env-custom-var": [
                                        {
                                            "key": "x-lae-env-custom-var",
                                            "value": "environment variable",
                                        }
                                    ],
                                },
                                "domainName": "www.example.com",
                                "keepaliveTimeout": 5,
                                "path": "",
                                "port": 80,
                                "protocol": "http",
                                "readTimeout": 30,
                                "sslProtocols": ["TLSv1", "TLSv1.1", "TLSv1.2"],
                            }
                        },
                        "querystring": query_string,
                        "uri": path,
                    },
                }
            }
        ]
    }

    if body is not None:
        event["Records"][0]["cf"]["request"]["body"] = {
            "inputTruncated": False,
            "action": "read-only",
            "encoding": "text",
            "data": body,
        }

    return dict(method=method, path=path, query_string=query_string, body=body, event=event)


@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_DEFAULT_REGION"] = "testing"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
