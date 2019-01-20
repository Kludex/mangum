import urllib.parse
import cgi

from mangum.handlers.asgi import ASGIHandler, ASGICycle


class AzureFunctionCycle(ASGICycle):
    def on_response_start(self, headers: dict, status_code: int) -> None:
        self.response["status_code"] = status_code
        self.response["headers"] = headers

        mimetype = None
        charset = None

        if "content-type" in headers:
            mimetype, options = cgi.parse_header(headers["content-type"])
            charset = options.get("charset", None)

        self.response["mimetype"] = mimetype
        self.response["charset"] = charset

    def on_response_body(self, body: bytes) -> None:
        self.response["body"] = body


class AzureFunctionHandler(ASGIHandler):
    asgi_cycle_class = AzureFunctionCycle


def azure_handler(app, req) -> dict:
    server = None
    client = None
    scheme = "https"
    method = req.method
    headers = req.headers.items()
    parsed = urllib.parse.urlparse(req.url)
    scheme = parsed.scheme
    path = parsed.path
    if req.params:
        query_string = urllib.parse.urlencode(req.params).encode("ascii")
    else:
        query_string = ""

    scope = {
        "type": "http",
        "server": server,
        "client": client,
        "method": method,
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
