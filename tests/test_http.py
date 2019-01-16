from mangum import asgi_response


class App:
    def __init__(self, scope) -> None:
        self.scope = scope

    async def __call__(self, receive, send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})


def test_asgi_response():
    event = {
        "headers": {},
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": None,
    }
    response = asgi_response(App, event, {})
    print(response)
