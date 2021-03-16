import base64
import gzip
import json
import urllib.parse

import pytest
import brotli
from brotli_asgi import BrotliMiddleware
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import PlainTextResponse
from mangum import Mangum


@pytest.mark.parametrize(
    "mock_http_event,query_string",
    [
        (["GET", None, None], b""),
        (["GET", None, {"name": ["me"]}], b"name=me"),
        (["GET", None, {"name": ["me", "you"]}], b"name=me&name=you"),
        (
            ["GET", None, {"name": ["me", "you"], "pet": ["dog"]}],
            b"name=me&name=you&pet=dog",
        ),
    ],
    indirect=["mock_http_event"],
)
def test_http_request(mock_http_event, query_string) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "body": None,
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, lzma, sdch, " "br",
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
                "httpMethod": "GET",
                "path": "/test/hello",
                "pathParameters": {"proxy": "hello"},
                "queryStringParameters": mock_http_event["queryStringParameters"],
                "multiValueQueryStringParameters": mock_http_event[
                    "multiValueQueryStringParameters"
                ],
                "requestContext": {
                    "accountId": "123456789012",
                    "apiId": "123",
                    "httpMethod": "GET",
                    "identity": {
                        "accountId": "",
                        "apiKey": "",
                        "caller": "",
                        "cognitoAuthenticationProvider": "",
                        "cognitoAuthenticationType": "",
                        "cognitoIdentityId": "",
                        "cognitoIdentityPoolId": "",
                        "sourceIp": "192.168.100.1",
                        "user": "",
                        "userAgent": "Mozilla/5.0 "
                        "(Macintosh; "
                        "Intel Mac OS "
                        "X 10_11_6) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like "
                        "Gecko) "
                        "Chrome/52.0.2743.82 "
                        "Safari/537.36 "
                        "OPR/39.0.2256.48",
                        "userArn": "",
                    },
                    "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
                    "resourceId": "us4z18",
                    "resourcePath": "/{proxy+}",
                    "stage": "Prod",
                },
                "resource": "/{proxy+}",
                "stageVariables": {"stageVarName": "stageVarValue"},
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [
                    b"accept",
                    b"text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                    b"webp,*/*;q=0.8",
                ],
                [b"accept-encoding", b"gzip, deflate, lzma, sdch, br"],
                [b"accept-language", b"en-US,en;q=0.8"],
                [b"cloudfront-forwarded-proto", b"https"],
                [b"cloudfront-is-desktop-viewer", b"true"],
                [b"cloudfront-is-mobile-viewer", b"false"],
                [b"cloudfront-is-smarttv-viewer", b"false"],
                [b"cloudfront-is-tablet-viewer", b"false"],
                [b"cloudfront-viewer-country", b"US"],
                [b"cookie", b"cookie1; cookie2"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"upgrade-insecure-requests", b"1"],
                [b"x-forwarded-for", b"192.168.100.1, 192.168.1.1"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/test/hello",
            "query_string": query_string,
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_lambda_at_edge_event",
    [
        (["GET", "/resource", None, None]),
        (["GET", "/resource/id", "filter=okay&hello=world", None]),
        (["POST", "/resource/id", "name=me", None])
    ],
    indirect=["mock_lambda_at_edge_event"],
)
def test_lambda_at_edge_http_request(mock_lambda_at_edge_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.eventType": "lambda@edge",
            "aws.event": {
                'Records': [
                    {
                        'cf': {
                            'config':  {
                                'distributionDomainName': 'mock-distribution.local.localhost',
                                'distributionId':         'ABC123DEF456G',
                                'eventType':              'origin-request',
                                'requestId':              'lBEBo2N0JKYUP2JXwn_4am2xAXB2GzcL2FlwXI8G59PA8wghF2ImFQ=='
                            },
                            'request': {
                                'clientIp':    '192.168.100.1',
                                'headers':     {
                                    'accept-encoding':   [
                                        {
                                            'key':   'accept-encoding',
                                            'value': 'gzip,deflate'
                                        }
                                    ],
                                    'x-forwarded-for':  [
                                        {
                                            'key':   'x-forwarded-for',
                                            'value': '192.168.100.1'
                                        }
                                    ],
                                    'x-forwarded-port':  [
                                        {
                                            'key':   'x-forwarded-port',
                                            'value': '443'
                                        }
                                    ],
                                    'x-forwarded-proto': [
                                        {
                                            'key':   'x-forwarded-proto',
                                            'value': 'https'
                                        }
                                    ],
                                    'host':           [
                                        {
                                            'key':   'host',
                                            'value': 'test.execute-api.us-west-2.amazonaws.com'
                                        }
                                    ]
                                },
                                'method':      mock_lambda_at_edge_event['method'],
                                'origin':      {
                                    'custom': {
                                        'customHeaders':    {
                                            'x-lae-env-custom-var': [
                                                {
                                                    'key':   'x-lae-env-custom-var',
                                                    'value': 'environment variable'
                                                }
                                            ]
                                        },
                                        'domainName':       'www.example.com',
                                        'keepaliveTimeout': 5,
                                        'path':             '',
                                        'port':             80,
                                        'protocol':         'http',
                                        'readTimeout':      30,
                                        'sslProtocols':     [
                                            'TLSv1',
                                            'TLSv1.1',
                                            'TLSv1.2'
                                        ]
                                    }
                                },
                                'querystring': mock_lambda_at_edge_event['query_string'],
                                'uri': mock_lambda_at_edge_event['path'],
                            }
                        }
                    }
                ]
            },
            "client":    ("192.168.100.1", 0),
            "headers":  [
                [b'accept-encoding', b'gzip,deflate'],
                [b'x-forwarded-port', b'443'],
                [b'x-forwarded-for', b'192.168.100.1'],
                [b'x-forwarded-proto', b'https'],
                [b'host', b'test.execute-api.us-west-2.amazonaws.com']
            ],
            "http_version": "1.1",
            "method": mock_lambda_at_edge_event['method'],
            "path": mock_lambda_at_edge_event['path'],
            "query_string": mock_lambda_at_edge_event['query_string'],
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": mock_lambda_at_edge_event['body']})

    handler = Mangum(app, lifespan="off")

    response = handler(mock_lambda_at_edge_event['event'], {})
    assert response == {
        "status": 200,
        "headers": {
            "content-type": [{
                "key": "content-type",
                "value": "text/plain; charset=utf-8"
            }]
        },
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_lambda_at_edge_event",
    [
        (["POST", "/resource/id", "name=me", b"Test body 1"])
    ],
    indirect=["mock_lambda_at_edge_event"],
)
def test_lambda_at_edge_http_request_with_body(mock_lambda_at_edge_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.eventType": "lambda@edge",
            "aws.event": {
                'Records': [
                    {
                        'cf': {
                            'config':  {
                                'distributionDomainName': 'mock-distribution.local.localhost',
                                'distributionId':         'ABC123DEF456G',
                                'eventType':              'origin-request',
                                'requestId':              'lBEBo2N0JKYUP2JXwn_4am2xAXB2GzcL2FlwXI8G59PA8wghF2ImFQ=='
                            },
                            'request': {
                                'clientIp':    '192.168.100.1',
                                'headers':     {
                                    'accept-encoding':   [
                                        {
                                            'key':   'accept-encoding',
                                            'value': 'gzip,deflate'
                                        }
                                    ],
                                    'x-forwarded-for':  [
                                        {
                                            'key':   'x-forwarded-for',
                                            'value': '192.168.100.1'
                                        }
                                    ],
                                    'x-forwarded-port':  [
                                        {
                                            'key':   'x-forwarded-port',
                                            'value': '443'
                                        }
                                    ],
                                    'x-forwarded-proto': [
                                        {
                                            'key':   'x-forwarded-proto',
                                            'value': 'https'
                                        }
                                    ],
                                    'host':           [
                                        {
                                            'key':   'host',
                                            'value': 'test.execute-api.us-west-2.amazonaws.com'
                                        }
                                    ]
                                },
                                'method':      mock_lambda_at_edge_event['method'],
                                'origin':      {
                                    'custom': {
                                        'customHeaders':    {
                                            'x-lae-env-custom-var': [
                                                {
                                                    'key':   'x-lae-env-custom-var',
                                                    'value': 'environment variable'
                                                }
                                            ]
                                        },
                                        'domainName':       'www.example.com',
                                        'keepaliveTimeout': 5,
                                        'path':             '',
                                        'port':             80,
                                        'protocol':         'http',
                                        'readTimeout':      30,
                                        'sslProtocols':     [
                                            'TLSv1',
                                            'TLSv1.1',
                                            'TLSv1.2'
                                        ]
                                    }
                                },
                                'querystring': mock_lambda_at_edge_event['query_string'],
                                'uri': mock_lambda_at_edge_event['path'],
                                "body": {
                                    "inputTruncated": False,
                                    "action":         "read-only",
                                    "encoding":       "text",
                                    "data":           mock_lambda_at_edge_event["body"]
                                }
                            }
                        }
                    }
                ]
            },
            "client":    ("192.168.100.1", 0),
            "headers":  [
                [b'accept-encoding', b'gzip,deflate'],
                [b'x-forwarded-port', b'443'],
                [b'x-forwarded-for', b'192.168.100.1'],
                [b'x-forwarded-proto', b'https'],
                [b'host', b'test.execute-api.us-west-2.amazonaws.com']
            ],
            "http_version": "1.1",
            "method": mock_lambda_at_edge_event['method'],
            "path": mock_lambda_at_edge_event['path'],
            "query_string": mock_lambda_at_edge_event['query_string'],
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": f"We received: {mock_lambda_at_edge_event['body'].decode('utf-8')}".encode()})

    handler = Mangum(app, lifespan="off")

    response = handler(mock_lambda_at_edge_event['event'], {})
    assert response == {
        "status": 200,
        "headers": {
            "content-type": [{
                "key": "content-type",
                "value": "text/plain; charset=utf-8"
            }]
        },
        "body": f"We received: {mock_lambda_at_edge_event['body'].decode('utf-8')}",
    }


@pytest.mark.parametrize(
    "mock_http_event", [["GET", None, {"name": ["me", "you"]}]], indirect=True
)
def test_http_response(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "body": None,
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, lzma, sdch, " "br",
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
                "httpMethod": "GET",
                "path": "/test/hello",
                "pathParameters": {"proxy": "hello"},
                "queryStringParameters": {"name": "me"},
                "multiValueQueryStringParameters": {"name": ["me", "you"]},
                "requestContext": {
                    "accountId": "123456789012",
                    "apiId": "123",
                    "httpMethod": "GET",
                    "identity": {
                        "accountId": "",
                        "apiKey": "",
                        "caller": "",
                        "cognitoAuthenticationProvider": "",
                        "cognitoAuthenticationType": "",
                        "cognitoIdentityId": "",
                        "cognitoIdentityPoolId": "",
                        "sourceIp": "192.168.100.1",
                        "user": "",
                        "userAgent": "Mozilla/5.0 "
                        "(Macintosh; "
                        "Intel Mac OS "
                        "X 10_11_6) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like "
                        "Gecko) "
                        "Chrome/52.0.2743.82 "
                        "Safari/537.36 "
                        "OPR/39.0.2256.48",
                        "userArn": "",
                    },
                    "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
                    "resourceId": "us4z18",
                    "resourcePath": "/{proxy+}",
                    "stage": "Prod",
                },
                "resource": "/{proxy+}",
                "stageVariables": {"stageVarName": "stageVarValue"},
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [
                    b"accept",
                    b"text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                    b"webp,*/*;q=0.8",
                ],
                [b"accept-encoding", b"gzip, deflate, lzma, sdch, br"],
                [b"accept-language", b"en-US,en;q=0.8"],
                [b"cloudfront-forwarded-proto", b"https"],
                [b"cloudfront-is-desktop-viewer", b"true"],
                [b"cloudfront-is-mobile-viewer", b"false"],
                [b"cloudfront-is-smarttv-viewer", b"false"],
                [b"cloudfront-is-tablet-viewer", b"false"],
                [b"cloudfront-viewer-country", b"US"],
                [b"cookie", b"cookie1; cookie2"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"upgrade-insecure-requests", b"1"],
                [b"x-forwarded-for", b"192.168.100.1, 192.168.1.1"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/test/hello",
            "query_string": b"name=me&name=you",
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/plain; charset=utf-8"],
                    [b"set-cookie", b"cookie1=cookie1; Secure"],
                    [b"set-cookie", b"cookie2=cookie2; Secure"],
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "multiValueHeaders": {
            "set-cookie": ["cookie1=cookie1; Secure", "cookie2=cookie2; Secure"]
        },
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_http_elb_singlevalue_event",
    [["GET", None, {"name": ["me", "you"]}]],
    indirect=True,
)
def test_elb_singlevalue_http_response(mock_http_elb_singlevalue_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "body": None,
                "isBase64Encoded": False,
                "headers": {
                    "accept-encoding": "gzip, deflate",
                    "cookie": "cookie1; cookie2",
                    "host": "test.execute-api.us-west-2.amazonaws.com",
                    "x-forwarded-for": "192.168.100.3, 192.168.100.2, 192.168.100.1",
                    "x-forwarded-port": "443",
                    "x-forwarded-proto": "https",
                },
                "httpMethod": "GET",
                "path": "/my/path",
                "queryStringParameters": {"name": "you"},
                "requestContext": {
                    "elb": {
                        "targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:0:targetgroup/test/0"
                    }
                },
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [b"accept-encoding", b"gzip, deflate"],
                [b"cookie", b"cookie1; cookie2"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"x-forwarded-for", b"192.168.100.3, 192.168.100.2, 192.168.100.1"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/my/path",
            "query_string": b"name=you",
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/plain; charset=utf-8"],
                    [b"set-cookie", b"cookie1=cookie1; Secure"],
                    [b"set-cookie", b"cookie2=cookie2; Secure"],
                    [b"set-cookie", b"cookie3=cookie3; Secure"],
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_elb_singlevalue_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {
            "content-type": "text/plain; charset=utf-8",
            "set-cookie": "cookie1=cookie1; Secure",
            "Set-cookie": "cookie2=cookie2; Secure",
            "sEt-cookie": "cookie3=cookie3; Secure",
        },
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_http_elb_multivalue_event",
    [["GET", None, {"name": ["me", "you"]}]],
    indirect=True,
)
def test_elb_multivalue_http_response(mock_http_elb_multivalue_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "body": None,
                "isBase64Encoded": False,
                "multiValueHeaders": {
                    "accept-encoding": ["gzip, deflate"],
                    "cookie": ["cookie1; cookie2"],
                    "host": ["test.execute-api.us-west-2.amazonaws.com"],
                    "x-forwarded-for": ["192.168.100.3, 192.168.100.2, 192.168.100.1"],
                    "x-forwarded-port": ["443"],
                    "x-forwarded-proto": ["https"],
                },
                "httpMethod": "GET",
                "path": "/my/path",
                "multiValueQueryStringParameters": {"name": ["me", "you"]},
                "requestContext": {
                    "elb": {
                        "targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:0:targetgroup/test/0"
                    }
                },
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [b"accept-encoding", b"gzip, deflate"],
                [b"cookie", b"cookie1; cookie2"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"x-forwarded-for", b"192.168.100.3, 192.168.100.2, 192.168.100.1"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/my/path",
            "query_string": b"name=me&name=you",
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/plain; charset=utf-8"],
                    [b"set-cookie", b"cookie1=cookie1; Secure"],
                    [b"set-cookie", b"cookie2=cookie2; Secure"],
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_elb_multivalue_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {},
        "multiValueHeaders": {
            "content-type": ["text/plain; charset=utf-8"],
            "set-cookie": ["cookie1=cookie1; Secure", "cookie2=cookie2; Secure"],
        },
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "123", None]], indirect=True)
def test_http_response_with_body(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"

        body = [b"4", b"5", b"6"]

        while True:
            message = await receive()
            if "body" in message:
                body.append(message["body"])

            if not message.get("more_body", False):
                body = b"".join(body)
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "456123",
    }


@pytest.mark.parametrize(
    "mock_http_event", [["GET", base64.b64encode(b"123"), None]], indirect=True
)
def test_http_binary_request_with_body(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"

        body = []
        message = await receive()

        if "body" in message:
            body.append(message["body"])

        if not message.get("more_body", False):

            body = b"".join(body)
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": body})

    mock_http_event["isBase64Encoded"] = True
    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "123",
    }


@pytest.mark.parametrize(
    "mock_http_event", [["GET", base64.b64encode(b"123"), None]], indirect=True
)
def test_http_binary_request_and_response(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"

        body = []
        message = await receive()

        if "body" in message:
            body.append(message["body"])

        if not message.get("more_body", False):

            body = b"".join(body)
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/octet-stream"]],
                }
            )
            await send({"type": "http.response.body", "body": b"abc"})

    mock_http_event["isBase64Encoded"] = True
    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {"content-type": "application/octet-stream"},
        "body": base64.b64encode(b"abc").decode(),
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_http_exception(mock_http_event) -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200})
        raise Exception()
        await send({"type": "http.response.body", "body": b"1", "more_body": True})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})

    assert response == {
        "body": "Internal Server Error",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }


@pytest.mark.parametrize("mock_http_event", [["GET", None, None]], indirect=True)
def test_http_exception_handler(mock_http_event) -> None:
    path = mock_http_event["path"]
    app = Starlette()

    @app.exception_handler(Exception)
    async def all_exceptions(request, exc):
        return PlainTextResponse(content="Error!", status_code=500)

    @app.route(path)
    def homepage(request):
        raise Exception()
        return PlainTextResponse("Hello, world!")

    handler = Mangum(app)
    response = handler(mock_http_event, {})

    assert response == {
        "body": "Error!",
        "headers": {"content-length": "6", "content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_cycle_state(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})
    assert response == {
        "body": "Internal Server Error",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.start", "status": 200})

    handler = Mangum(app, lifespan="off")

    response = handler(mock_http_event, {})
    assert response == {
        "body": "Internal Server Error",
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "isBase64Encoded": False,
        "statusCode": 500,
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_api_gateway_base_path(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        assert scope["path"] == urllib.parse.unquote(mock_http_event["path"])
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"Hello world!"})

    handler = Mangum(app, lifespan="off", api_gateway_base_path=None)
    response = handler(mock_http_event, {})

    assert response == {
        "body": "Hello world!",
        "headers": {},
        "isBase64Encoded": False,
        "statusCode": 200,
    }

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        assert scope["path"] == urllib.parse.unquote(
            mock_http_event["path"][len(f"/{api_gateway_base_path}") :]
        )
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"Hello world!"})

    api_gateway_base_path = "test"
    handler = Mangum(app, lifespan="off", api_gateway_base_path=api_gateway_base_path)
    response = handler(mock_http_event, {})
    assert response == {
        "body": "Hello world!",
        "headers": {},
        "isBase64Encoded": False,
        "statusCode": 200,
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_text_mime_types(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(
        app, lifespan="off", text_mime_types=["application/vnd.apple.pkpass"]
    )
    response = handler(mock_http_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_binary_gzip_response(mock_http_event) -> None:
    body = json.dumps({"abc": "defg"})

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            }
        )

        await send({"type": "http.response.body", "body": body.encode()})

    handler = Mangum(GZipMiddleware(app, minimum_size=1), lifespan="off")
    response = handler(mock_http_event, {})

    assert response["isBase64Encoded"]
    assert response["headers"] == {
        "content-encoding": "gzip",
        "content-type": "application/json",
        "content-length": "35",
        "vary": "Accept-Encoding",
    }
    assert response["body"] == base64.b64encode(gzip.compress(body.encode())).decode()


@pytest.mark.parametrize(
    "mock_http_api_event",
    [
        (["GET", None, None, ""]),
        (["GET", None, {"name": ["me"]}, "name=me"]),
        (["GET", None, {"name": ["me", "you"]}, "name=me&name=you"]),
        (
            [
                "GET",
                None,
                {"name": ["me", "you"], "pet": ["dog"]},
                "name=me&name=you&pet=dog",
            ]
        ),
    ],
    indirect=["mock_http_api_event"],
)
def test_api_request(mock_http_api_event) -> None:
    async def app(scope, receive, send):
        assert scope == {
            "asgi": {"version": "3.0"},
            "aws.context": {},
            "aws.event": {
                "version": "2.0",
                "routeKey": "$default",
                "rawPath": "/my/path",
                "rawQueryString": mock_http_api_event["rawQueryString"],
                "cookies": ["cookie1", "cookie2"],
                "headers": {
                    "accept-encoding": "gzip,deflate",
                    "x-forwarded-port": "443",
                    "x-forwarded-proto": "https",
                    "host": "test.execute-api.us-west-2.amazonaws.com",
                },
                "queryStringParameters": mock_http_api_event["queryStringParameters"],
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
                        "method": "GET",
                        "path": "/my/path",
                        "protocol": "HTTP/1.1",
                        "sourceIp": "192.168.100.1",
                        "userAgent": "agent",
                    },
                    "requestId": "id",
                    "routeKey": "$default",
                    "stage": "$default",
                    "time": "12/Mar/2020:19:03:58 +0000",
                    "timeEpoch": 1_583_348_638_390,
                },
                "body": None,
                "pathParameters": {"parameter1": "value1"},
                "isBase64Encoded": False,
                "stageVariables": {
                    "stageVariable1": "value1",
                    "stageVariable2": "value2",
                },
            },
            "client": ("192.168.100.1", 0),
            "headers": [
                [b"accept-encoding", b"gzip,deflate"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"cookie", b"cookie1; cookie2"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/my/path",
            "query_string": mock_http_api_event["rawQueryString"].encode(),
            "raw_path": None,
            "root_path": "",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 443),
            "type": "http",
        }

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/plain; charset=utf-8"],
                    [b"set-cookie", b"cookie1=cookie1; Secure"],
                    [b"set-cookie", b"cookie2=cookie2; Secure"],
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_api_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "cookies": ["cookie1=cookie1; Secure", "cookie2=cookie2; Secure"],
        "body": "Hello, world!",
    }


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_empty_header(mock_http_event) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")

    mock_http_event["headers"] = None

    response = handler(mock_http_event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "mock_http_event,response_headers,expected_headers,expected_multi_value_headers",
    [
        [
            ["GET", None, None],
            [[b"key1", b"value1"], [b"key2", b"value2"]],
            {"key1": "value1", "key2": "value2"},
            {},
        ],
        [
            ["GET", None, None],
            [[b"key1", b"value1"], [b"key1", b"value2"]],
            {},
            {"key1": ["value1", "value2"]},
        ],
        [
            ["GET", None, None],
            [[b"key1", b"value1"], [b"key1", b"value2"], [b"key1", b"value3"]],
            {},
            {"key1": ["value1", "value2", "value3"]},
        ],
        [["GET", None, None], [], {}, {}],
    ],
    indirect=["mock_http_event"],
)
def test_http_response_headers(
    mock_http_event, response_headers, expected_headers, expected_multi_value_headers
) -> None:
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]]
                + response_headers,
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    handler = Mangum(app, lifespan="off")
    response = handler(mock_http_event, {})
    expected = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }
    if expected_headers:
        expected["headers"].update(expected_headers)
    if expected_multi_value_headers:
        expected["multiValueHeaders"] = expected_multi_value_headers
    assert response == expected


@pytest.mark.parametrize("mock_http_event", [["GET", "", None]], indirect=True)
def test_http_binary_br_response(mock_http_event) -> None:
    body = json.dumps({"abc": "defg"})

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            }
        )

        await send({"type": "http.response.body", "body": body.encode()})

    handler = Mangum(BrotliMiddleware(app, minimum_size=1), lifespan="off")
    response = handler(mock_http_event, {})

    assert response["isBase64Encoded"]
    assert response["headers"] == {
        "content-encoding": "br",
        "content-type": "application/json",
        "content-length": "19",
        "vary": "Accept-Encoding",
    }
    assert response["body"] == base64.b64encode(brotli.compress(body.encode())).decode()
