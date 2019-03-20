import base64
from mangum import Mangum


def test_aws_response(mock_data) -> None:
    def app(scope):
        assert scope["type"] == "http"

        async def asgi(receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello, world!"})

        return asgi

    mock_event = mock_data.get_aws_event()
    mock_event["headers"]["Host"] = "127.0.0.1:3000"
    handler = Mangum(app)
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "Hello, world!",
    }


def test_aws_response_body(mock_data) -> None:
    def app(scope):
        assert scope["type"] == "http"

        async def asgi(receive, send):
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
                            "headers": [
                                [b"content-type", b"text/plain; charset=utf-8"]
                            ],
                        }
                    )
                    await send({"type": "http.response.body", "body": body})
                    return

        return asgi

    mock_event = mock_data.get_aws_event(body="123")
    handler = Mangum(app)
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": "456123",
    }


def test_aws_binary_response_body(mock_data) -> None:
    def app(scope):
        assert scope["type"] == "http"

        async def asgi(receive, send):
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
                return

        return asgi

    body_encoded = base64.b64encode(b"123")
    mock_event = mock_data.get_aws_event(body=body_encoded)
    mock_event["isBase64Encoded"] = True
    handler = Mangum(app)
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": body_encoded.decode(),
    }


def test_aws_debug(mock_data) -> None:
    def app(scope):
        assert scope["type"] == "http"

        async def asgi(receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
                }
            )
            raise Exception("Error!")
            await send({"type": "http.response.body", "body": b"Hello, world!"})

        return asgi

    mock_event = mock_data.get_aws_event()
    handler = Mangum(app, debug=True)
    response = handler(mock_event, {})

    assert response["statusCode"] == 500
    assert not response["isBase64Encoded"]
    assert response["headers"] == {"content-type": "text/plain; charset=utf-8"}
    assert response["body"].split()[0] == "Traceback"
