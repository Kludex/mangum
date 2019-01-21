import urllib.parse

from azure.functions import HttpResponse
from mangum.handlers.asgi import ASGICycle
from mangum.utils import encode_query_string


class AzureFunctionCycle(ASGICycle):
    def on_response_start(self, headers: dict, status_code: int) -> None:
        self.response["status_code"] = status_code
        self.response["headers"] = headers
        if self.mimetype:
            self.response["mimetype"] = self.mimetype
        if self.charset:
            self.response["charset"] = self.charset

    def on_response_body(self, body: bytes) -> None:
        self.response["body"] = body


def azure_handler(app, req) -> dict:

    server = None
    client = None
    scheme = "https"
    method = req.method
    headers = req.headers.items()
    parsed = urllib.parse.urlparse(req.url)
    scheme = parsed.scheme
    path = parsed.path
    query_string = encode_query_string(req.params) if req.params else ""

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

    body = req.get_body() or b""

    asgi_cycle = AzureFunctionCycle(scope, body=body)
    response = asgi_cycle(app)

    return HttpResponse(
        body=response["body"],
        headers=response["headers"],
        status_code=response["status_code"],
        mimetype=response["mimetype"],
        charset=response["charset"],
    )
