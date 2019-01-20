import urllib.parse
from mangum.handlers.asgi import ASGIHandler, ASGICycle


class AzureFunctionCycle(ASGICycle):
    def on_response_start(self, headers, status_code):
        self.response["status_code"] = status_code

    def on_response_body(self, body):
        self.response["body"] = body


class AzureFunctionHandler(ASGIHandler):
    asgi_cycle_class = AzureFunctionCycle


def azure_handler(app, req) -> dict:
    server = None
    client = None
    scheme = "https"

    headers = req.headers.items()
    path = req.url

    if req.params:
        query_string = urllib.parse.urlencode(req.params).encode("ascii")
    else:
        query_string = ""

    scope = {
        "type": "http",
        "server": server,
        "client": client,
        "method": req.method,
        "path": path,
        "scheme": scheme,
        "http_version": "1.1",
        "root_path": "",
        "query_string": query_string,
        "headers": headers,
    }

    body = b""
    more_body = False

    message = {"type": "http.request", "body": body, "more_body": more_body}

    handler = AzureFunctionHandler(scope)
    return handler(app, message)
