import pytest
import typing
from collections import defaultdict

@pytest.fixture
def mock_http_event(request):
    method = request.param[0]
    body = request.param[1]
    multi_value_query_parameters = request.param[2]
    headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, lzma, sdch, br",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Host": "test.execute-api.us-west-2.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-For": "192.168.100.1, 192.168.1.1",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
    }
    event = {
        "path": "/test/hello",
        "body": body,
        "headers": headers,
        "multiValueHeaders": {h: [v] for h, v in headers.items()}, # API GW docs suggest these are always present.
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
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
                "user": "",
            },
            "resourcePath": "/{proxy+}",
            "httpMethod": method,
            "apiId": "123",
        },
        "resource": "/{proxy+}",
        "httpMethod": method,
        "queryStringParameters": {
            k: v[0] for k, v in multi_value_query_parameters.items()
        }
        if multi_value_query_parameters
        else None,
        "multiValueQueryStringParameters": multi_value_query_parameters or None,
        "stageVariables": {"stageVarName": "stageVarValue"},
    }
    return event


@pytest.fixture
def mock_http_api_event(request):
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
        "queryStringParameters": {
            k: v[0] for k, v in multi_value_query_parameters.items()
        }
        if multi_value_query_parameters
        else None,
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
def mock_alb_event(request):
    method = request.param[0]
    use_multi_value_headers = request.param[1]

    mvHeaders = {
        'accept': ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'],
        'accept-encoding': ['gzip'],
        'accept-language': ['en-US,en;q=0.5'],
        'connection': ['keep-alive'],
        'cookie': ['name=value'],
        'host': ['lambda-YYYYYYYY.elb.amazonaws.com'],
        'upgrade-insecure-requests': ['1'],
        'user-agent': ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:60.0) Gecko/20100101 Firefox/60.0'],
        'x-amzn-trace-id': ['Root=1-5bdb40ca-556d8b0c50dc66f0511bf520'],
        'x-forwarded-for': ['192.0.2.1'],
        'x-forwarded-port': ['80'],
        'x-forwarded-proto': ['http']
    }

    event = {
        'requestContext': {
            'elb': {
                'targetGroupArn': 'arn:aws:elasticloadbalancing:us-east-1:XXXXXXXXXXX:targetgroup/sample/6d0ecf831eec9f09'
            }
        },
        'httpMethod': method,
        'path': '/',
        'body': '',
        'isBase64Encoded': False
    }

    if use_multi_value_headers:
        event["multiValueHeaders"] = mvHeaders
        event["multiValueQueryStringParameters"] = {}
    else:
        event["headers"] = {h: vv[0] for h, vv in mvHeaders.items()}
        event["queryStringParameters"] = {}

    return event