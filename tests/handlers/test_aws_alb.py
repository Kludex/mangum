import pytest

from mangum import Mangum
from mangum.handlers import AwsAlb


def get_mock_aws_alb_event(
    method, path, multi_value_query_parameters, body, body_base64_encoded
):
    return {
        "requestContext": {
            "elb": {
                "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-2:123456789012:targetgroup/lambda-279XGJDqGZ5rsrHC2Fjr/49e9d65c45c6791a"  # noqa: E501
            }
        },
        "httpMethod": method,
        "path": path,
        "multiValueQueryStringParameters": multi_value_query_parameters
        if multi_value_query_parameters
        else {},
        "headers": {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,image/apng,*/*;q=0.8",
            "accept-encoding": "gzip",
            "accept-language": "en-US,en;q=0.9",
            "connection": "keep-alive",
            "host": "lambda-alb-123578498.us-east-2.elb.amazonaws.com",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/71.0.3578.98 Safari/537.36",
            "x-amzn-trace-id": "Root=1-5c536348-3d683b8b04734faae651f476",
            "x-forwarded-for": "72.12.164.125",
            "x-forwarded-port": "80",
            "x-forwarded-proto": "http",
            "x-imforwards": "20",
        },
        "body": body,
        "isBase64Encoded": body_base64_encoded,
    }


def test_aws_alb_basic():
    """
    Test the event from the AWS docs
    """
    example_event = {
        "requestContext": {
            "elb": {
                "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-2:123456789012:targetgroup/lambda-279XGJDqGZ5rsrHC2Fjr/49e9d65c45c6791a"  # noqa: E501
            }
        },
        "httpMethod": "GET",
        "path": "/lambda",
        "queryStringParameters": {
            "q1": "1234ABCD",
            "q2": "b+c",  # not encoded
            "q3": "b%20c",  # encoded
            "q4": "/some/path/",  # not encoded
            "q5": "%2Fsome%2Fpath%2F",  # encoded
        },
        "headers": {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,image/apng,*/*;q=0.8",
            "accept-encoding": "gzip",
            "accept-language": "en-US,en;q=0.9",
            "connection": "keep-alive",
            "host": "lambda-alb-123578498.us-east-2.elb.amazonaws.com",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",  # noqa: E501
            "x-amzn-trace-id": "Root=1-5c536348-3d683b8b04734faae651f476",
            "x-forwarded-for": "72.12.164.125",
            "x-forwarded-port": "80",
            "x-forwarded-proto": "http",
            "x-imforwards": "20",
        },
        "body": "",
        "isBase64Encoded": False,
    }

    example_context = {}
    handler = AwsAlb(example_event, example_context)
    assert handler.request.scope == {
        "asgi": {"version": "3.0"},
        "aws.context": {},
        "aws.event": example_event,
        "aws.eventType": "AWS_ALB",
        "client": ("72.12.164.125", 0),
        "headers": [
            [
                b"accept",
                b"text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                b"webp,image/apng,*/*;q=0.8",
            ],
            [b"accept-encoding", b"gzip"],
            [b"accept-language", b"en-US,en;q=0.9"],
            [b"connection", b"keep-alive"],
            [b"host", b"lambda-alb-123578498.us-east-2.elb.amazonaws.com"],
            [b"upgrade-insecure-requests", b"1"],
            [
                b"user-agent",
                b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                b" (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
            ],
            [b"x-amzn-trace-id", b"Root=1-5c536348-3d683b8b04734faae651f476"],
            [b"x-forwarded-for", b"72.12.164.125"],
            [b"x-forwarded-port", b"80"],
            [b"x-forwarded-proto", b"http"],
            [b"x-imforwards", b"20"],
        ],
        "http_version": "1.1",
        "method": "GET",
        "path": "/lambda",
        "query_string": b"q1=1234ABCD&q2=b+c&q3=b+c&q4=%2Fsome%2Fpath%2F&q5=%2Fsome%2Fpath%2F",
        "raw_path": None,
        "root_path": "",
        "scheme": "http",
        "server": ("lambda-alb-123578498.us-east-2.elb.amazonaws.com", 80),
        "type": "http",
    }


@pytest.mark.parametrize(
    "method,path,multi_value_query_parameters,req_body,body_base64_encoded,"
    "query_string,scope_body",
    [
        ("GET", "/hello/world", None, None, False, b"", None),
        ("POST", "/", {"name": ["me"]}, None, False, b"name=me", None),
        (
            "GET",
            "/my/resource",
            {"name": ["me", "you"]},
            None,
            False,
            b"name=me&name=you",
            None,
        ),
        (
            "GET",
            "",
            {"name": ["me", "you"], "pet": ["dog"]},
            None,
            False,
            b"name=me&name=you&pet=dog",
            None,
        ),
        # A 1x1 red px gif
        (
            "POST",
            "/img",
            None,
            b"R0lGODdhAQABAIABAP8AAAAAACwAAAAAAQABAAACAkQBADs=",
            True,
            b"",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\xff\x00\x00\x00\x00\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
        ),
        ("POST", "/form-submit", None, b"say=Hi&to=Mom", False, b"", b"say=Hi&to=Mom"),
    ],
)
def test_aws_alb_scope_real(
    method,
    path,
    multi_value_query_parameters,
    req_body,
    body_base64_encoded,
    query_string,
    scope_body,
):
    event = get_mock_aws_alb_event(
        method, path, multi_value_query_parameters, req_body, body_base64_encoded
    )
    example_context = {}
    handler = AwsAlb(event, example_context)

    scope_path = path
    if scope_path == "":
        scope_path = "/"

    assert handler.request.scope == {
        "asgi": {"version": "3.0"},
        "aws.context": {},
        "aws.event": event,
        "aws.eventType": "AWS_ALB",
        "client": ("72.12.164.125", 0),
        "headers": [
            [
                b"accept",
                b"text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                b"webp,image/apng,*/*;q=0.8",
            ],
            [b"accept-encoding", b"gzip"],
            [b"accept-language", b"en-US,en;q=0.9"],
            [b"connection", b"keep-alive"],
            [b"host", b"lambda-alb-123578498.us-east-2.elb.amazonaws.com"],
            [b"upgrade-insecure-requests", b"1"],
            [
                b"user-agent",
                b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                b" (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
            ],
            [b"x-amzn-trace-id", b"Root=1-5c536348-3d683b8b04734faae651f476"],
            [b"x-forwarded-for", b"72.12.164.125"],
            [b"x-forwarded-port", b"80"],
            [b"x-forwarded-proto", b"http"],
            [b"x-imforwards", b"20"],
        ],
        "http_version": "1.1",
        "method": method,
        "path": scope_path,
        "query_string": query_string,
        "raw_path": None,
        "root_path": "",
        "scheme": "http",
        "server": ("lambda-alb-123578498.us-east-2.elb.amazonaws.com", 80),
        "type": "http",
    }

    assert handler.body == scope_body


def test_aws_alb_set_cookies() -> None:
    async def app(scope, receive, send):
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
    event = get_mock_aws_alb_event("GET", "/test", {}, None, False)
    response = handler(event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "multiValueHeaders": {
            "set-cookie": ["cookie1=cookie1; Secure", "cookie2=cookie2; Secure"],
        },
        "body": "Hello, world!",
    }


@pytest.mark.parametrize(
    "method,content_type,raw_res_body,res_body,res_base64_encoded",
    [
        ("GET", b"text/plain; charset=utf-8", b"Hello world", "Hello world", False),
        # A 1x1 red px gif
        (
            "POST",
            b"image/gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\xff\x00\x00\x00\x00\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            "R0lGODdhAQABAIABAP8AAAAAACwAAAAAAQABAAACAkQBADs=",
            True,
        ),
    ],
)
def test_aws_alb_response(
    method, content_type, raw_res_body, res_body, res_base64_encoded
):
    async def app(scope, receive, send):
        assert scope["aws.eventType"] == "AWS_ALB"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", content_type]],
            }
        )
        await send({"type": "http.response.body", "body": raw_res_body})

    event = get_mock_aws_alb_event(method, "/test", {}, None, False)

    handler = Mangum(app, lifespan="off")

    response = handler(event, {})
    assert response == {
        "statusCode": 200,
        "isBase64Encoded": res_base64_encoded,
        "headers": {"content-type": content_type.decode()},
        "multiValueHeaders": {},
        "body": res_body,
    }
