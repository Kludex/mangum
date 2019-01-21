import base64
from mangum.handlers.asgi import ASGICycle
from mangum.utils import encode_query_string


class AWSLambdaCycle(ASGICycle):
    def __init__(self, *args, **kwargs) -> None:
        self.binary = kwargs.pop("binary", False)
        super().__init__(*args, **kwargs)

    def on_response_start(self, headers: dict, status_code: int) -> None:
        self.response["statusCode"] = status_code
        self.response["isBase64Encoded"] = self.binary
        self.response["headers"] = headers

    def on_response_body(self, body: bytes) -> None:
        if self.binary:
            body = base64.b64encode(body)
        else:
            body = body.decode("ascii")

        self.response["body"] = body


def aws_handler(app, event: dict, context: dict) -> dict:
    server = None
    client = None
    method = event["httpMethod"]
    headers = event["headers"] or {}
    path = event["path"]
    host = headers.get("Host")
    scheme = headers.get("X-Forwarded-Proto", "http")
    x_forwarded_for = headers.get("X-Forwarded-For")
    x_forwarded_port = headers.get("X-Forwarded-Port")

    if x_forwarded_port and x_forwarded_for:
        port = int(x_forwarded_port)
        client = (x_forwarded_for, port)
        if host:
            server = (host, port)

    query_string_params = event["queryStringParameters"]
    query_string = (
        encode_query_string(query_string_params) if query_string_params else ""
    )

    scope = {
        "server": server,
        "client": client,
        "scheme": scheme,
        "root_path": "",
        "query_string": query_string,
        "headers": headers.items(),
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
    }

    binary = event.get("isBase64Encoded", False)

    if binary:
        encoded = event["body"]
        body = base64.b64decode(encoded)
    else:
        body = event["body"]

    if not isinstance(body, bytes):
        body = body.encode("utf-8")

    handler = AWSLambdaCycle(scope, body=body, binary=binary)
    return handler(app)
