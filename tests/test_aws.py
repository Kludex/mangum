import base64
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from mangum.handlers.aws import aws_handler


def get_mock_event() -> dict:
    event = {
        "path": "/test/hello",
        "body": "123",
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
            "Host": "wt6mne2s9k.execute-api.us-west-2.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
            "Via": "1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)",
            "X-Amz-Cf-Id": "nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==",
            "X-Forwarded-For": "192.168.100.1, 192.168.1.1",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
        },
        "pathParameters": {"proxy": "hello"},
        "requestContext": {
            "accountId": "123456789012",
            "resourceId": "us4z18",
            "stage": "test",
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
            "httpMethod": "GET",
            "apiId": "wt6mne2s9k",
        },
        "resource": "/{proxy+}",
        "httpMethod": "GET",
        "queryStringParameters": {"name": "me"},
        "stageVariables": {"stageVarName": "stageVarValue"},
    }
    return event


def test_aws_response() -> None:
    def app(scope):
        async def asgi(receive, send):
            response = PlainTextResponse("Hello, world!")
            await response(receive, send)

        return asgi

    mock_event = get_mock_event()
    response = aws_handler(app, mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {
            "content-length": "13",
            "content-type": "text/plain; charset=utf-8",
        },
        "body": "Hello, world!",
    }


def test_aws_response_with_body() -> None:
    def app(scope):
        async def asgi(receive, send):
            request = Request(scope, receive)
            body = await request.body()
            response = PlainTextResponse(body)
            await response(receive, send)

        return asgi

    mock_event = get_mock_event()
    response = aws_handler(app, mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-length": "3", "content-type": "text/plain; charset=utf-8"},
        "body": "123",
    }


def test_aws_binary_response_with_body() -> None:
    def app(scope):
        async def asgi(receive, send):
            message = await receive()
            body = message["body"]
            response = PlainTextResponse(body)
            await response(receive, send)

        return asgi

    mock_event = get_mock_event()
    body = b"123"
    body_encoded = base64.b64encode(body)
    mock_event["body"] = body_encoded
    mock_event["isBase64Encoded"] = True
    response = aws_handler(app, mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {"content-length": "3", "content-type": "text/plain; charset=utf-8"},
        "body": body_encoded,
    }


def test_starlette_aws_response() -> None:

    mock_event = get_mock_event()

    app = Starlette()

    @app.route(mock_event["path"])
    def homepage(request):
        return PlainTextResponse("Hello, world!")

    response = aws_handler(app, mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {
            "content-length": "13",
            "content-type": "text/plain; charset=utf-8",
        },
        "body": "Hello, world!",
    }
