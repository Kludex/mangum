from mangum.types import EventSource

import pytest


@pytest.mark.parametrize(
    "event,event_source",
    [
        (
            {
                "body": '{"username":"xyz","password":"xyz"}',
                "headers": {
                    "accept": "*/*",
                    "content-length": "35",
                    "content-type": "application/json",
                    "head": "abc",
                    "host": "test-755069476.eu-central-1.elb.amazonaws.com",
                    "user-agent": "curl/7.54.0",
                    "x-amzn-trace-id": "Root=1-5fff2c3d-02201fad1b80d4fe331120e7",
                    "x-forwarded-for": "77.79.170.37",
                    "x-forwarded-port": "80",
                    "x-forwarded-proto": "http",
                },
                "httpMethod": "POST",
                "isBase64Encoded": False,
                "path": "/user/id/123123",
                "queryStringParameters": {"a": "bar", "q": "baz"},
                "requestContext": {
                    "elb": {
                        "targetGroupArn": (
                            "arn:aws:elasticloadbalancing:eu-central-1:123:"
                            "targetgroup/lambda/6a653f0ffbc88fec"
                        )
                    },
                },
            },
            EventSource.ALB,
        ),
        (
            {
                "body": '{"username":"xyz","password":"xyz"}',
                "httpMethod": "POST",
                "isBase64Encoded": False,
                "multiValueHeaders": {
                    "accept": ["*/*"],
                    "content-length": ["35"],
                    "content-type": ["application/json"],
                    "head": ["123", "abc"],
                    "host": ["test-755069476.eu-central-1.elb.amazonaws.com"],
                    "user-agent": ["curl/7.54.0"],
                    "x-amzn-trace-id": ["Root=1-5fff2c9e-554de4de50c1c373369d2ba9"],
                    "x-forwarded-for": ["77.79.170.37"],
                    "x-forwarded-port": ["80"],
                    "x-forwarded-proto": ["http"],
                },
                "multiValueQueryStringParameters": {"a": ["bar"], "q": ["foo", "baz"]},
                "path": "/user/id/123123",
                "requestContext": {
                    "elb": {
                        "targetGroupArn": (
                            "arn:aws:elasticloadbalancing:eu-central-1:123:"
                            "targetgroup/lambda/6a653f0ffbc88fec"
                        )
                    }
                },
            },
            EventSource.ALB_MULTIVALUEHEADERS,
        ),
        (
            {
                "body": '{"username":"xyz","password":"xyz"}',
                "headers": {
                    "Content-Length": "35",
                    "Content-Type": "application/json",
                    "Cookie": "foo=bar",
                    "Host": "pr3k5m9ob8.execute-api.eu-central-1.amazonaws.com",
                    "User-Agent": "curl/7.54.0",
                    "X-Amzn-Trace-Id": "Root=1-5fffc75d-272ca7e75cb8ec6a02f15752",
                    "X-Forwarded-For": "77.79.170.37",
                    "X-Forwarded-Port": "443",
                    "X-Forwarded-Proto": "https",
                    "accept": "*/*",
                    "head": "abc",
                },
                "httpMethod": "POST",
                "isBase64Encoded": False,
                "multiValueHeaders": {
                    "Content-Length": ["35"],
                    "Content-Type": ["application/json"],
                    "Cookie": ["foo=bar"],
                    "Host": ["pr3k5m9ob8.execute-api.eu-central-1.amazonaws.com"],
                    "User-Agent": ["curl/7.54.0"],
                    "X-Amzn-Trace-Id": ["Root=1-5fffc75d-272ca7e75cb8ec6a02f15752"],
                    "X-Forwarded-For": ["77.79.170.37"],
                    "X-Forwarded-Port": ["443"],
                    "X-Forwarded-Proto": ["https"],
                    "accept": ["*/*"],
                    "head": ["123", "abc"],
                },
                "multiValueQueryStringParameters": {"a": ["bar"], "q": ["foo", "baz"]},
                "path": "/logger",
                "pathParameters": None,
                "queryStringParameters": {"a": "bar", "q": "baz"},
                "requestContext": {
                    "accountId": "386635533411",
                    "apiId": "pr3k5m9ob8",
                    "domainName": "pr3k5m9ob8.execute-api.eu-central-1.amazonaws.com",
                    "domainPrefix": "pr3k5m9ob8",
                    "extendedRequestId": "ZHwWkiwKliAEJNg=",
                    "httpMethod": "POST",
                    "identity": {
                        "accessKey": None,
                        "accountId": None,
                        "caller": None,
                        "cognitoAmr": None,
                        "cognitoAuthenticationProvider": None,
                        "cognitoAuthenticationType": None,
                        "cognitoIdentityId": None,
                        "cognitoIdentityPoolId": None,
                        "principalOrgId": None,
                        "sourceIp": "77.79.170.37",
                        "user": None,
                        "userAgent": "curl/7.54.0",
                        "userArn": None,
                    },
                    "path": "/logger",
                    "protocol": "HTTP/1.1",
                    "requestId": "ZHwWkiwKliAEJNg=",
                    "requestTime": "14/Jan/2021:04:23:57 +0000",
                    "requestTimeEpoch": 1610598237125,
                    "resourceId": "ANY /logger",
                    "resourcePath": "/logger",
                    "stage": "$default",
                },
                "resource": "/logger",
                "stageVariables": None,
                "version": "1.0",
            },
            EventSource.API_GW_V1,
        ),
        (
            {
                "body": '{"username":"xyz","password":"xyz"}',
                "cookies": ["foo=bar"],
                "headers": {
                    "accept": "*/*",
                    "content-length": "35",
                    "content-type": "application/json",
                    "head": "123,abc",
                    "host": "pr3k5m9ob8.execute-api.eu-central-1.amazonaws.com",
                    "user-agent": "curl/7.54.0",
                    "x-amzn-trace-id": "Root=1-5fffc60e-1679fb5a1d62219d67db18e1",
                    "x-forwarded-for": "77.79.170.37",
                    "x-forwarded-port": "443",
                    "x-forwarded-proto": "https",
                },
                "isBase64Encoded": False,
                "queryStringParameters": {"a": "bar", "q": "foo,baz"},
                "rawPath": "/logger",
                "rawQueryString": "q=foo&a=bar&q=baz",
                "requestContext": {
                    "accountId": "386635533411",
                    "apiId": "pr3k5m9ob8",
                    "domainName": "pr3k5m9ob8.execute-api.eu-central-1.amazonaws.com",
                    "domainPrefix": "pr3k5m9ob8",
                    "http": {
                        "method": "POST",
                        "path": "/logger",
                        "protocol": "HTTP/1.1",
                        "sourceIp": "77.79.170.37",
                        "userAgent": "curl/7.54.0",
                    },
                    "requestId": "ZHviWj0LliAEMig=",
                    "routeKey": "ANY /logger",
                    "stage": "$default",
                    "time": "14/Jan/2021:04:18:22 +0000",
                    "timeEpoch": 1610597902927,
                },
                "routeKey": "ANY /logger",
                "version": "2.0",
            },
            EventSource.API_GW_V2,
        ),
    ],
)
def test_event_source_detection(event, event_source):
    assert EventSource.get_event_source(event) == event_source
