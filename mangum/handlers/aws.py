import urllib.parse
from mangum.handlers.asgi import ASGIHandler, ASGICycle


class AWSLambdaCycle(ASGICycle):
    def on_response_start(self, headers: list, status_code: int) -> None:
        self.response["statusCode"] = status_code
        self.response["isBase64Encoded"] = False
        self.response["headers"] = {
            k.decode("utf-8"): v.decode("utf-8") for k, v in headers
        }

    def on_response_body(self, body: str) -> None:
        self.response["body"] = body


class AWSLambdaHandler(ASGIHandler):
    asgi_cycle_class = AWSLambdaCycle


def aws_handler(app, event: dict, context: dict) -> dict:
    headers = event["headers"] or {}
    host = headers.get("Host")
    scheme = headers.get("X-Forwarded-Proto", "http")
    x_forwarded_for = headers.get("X-Forwarded-For")
    x_forwarded_port = headers.get("X-Forwarded-Port")
    client = None
    server = None

    if x_forwarded_port and x_forwarded_for:
        port = int(x_forwarded_port)
        client = (x_forwarded_for, port)
        if host:
            server = (host, port)

    query_string = ""
    if "queryStringParameters" in event:
        query_string_params = event["queryStringParameters"]
        if query_string_params:
            query_string = urllib.parse.urlencode(query_string_params).encode("ascii")

    scope = {
        "server": server,
        "client": client,
        "scheme": scheme,
        "root_path": "",
        "query_string": query_string,
        "headers": headers.items(),
        "type": "http",
        "http_version": "1.1",
        "method": event["httpMethod"],
        "path": event["path"],
    }

    body = b""
    more_body = False
    message = {"type": "http.request", "body": body, "more_body": more_body}
    handler = AWSLambdaHandler(scope)

    return handler(app, message)
