import urllib.parse
from azure.functions import HttpRequest, HttpResponse
from mangum.asgi.protocol import ASGICycle
from mangum.asgi.middleware import ServerlessMiddleware
from mangum.utils import encode_query_string


class AzureFunctionCycle(ASGICycle):
    """
    An adapter that handles the HTTP request-response cycle for an ASGI application and
    builds a valid response to return to Azure Functions.

    The response is a Python dictionary with the following structure:

        {
            "body": bytes,
            "charset": str,
            "headers": dict,
            "mimetype": str,
            "status_code": itnt
        }
    """

    def on_response_start(self, headers: dict, status_code: int) -> None:
        self.response["status_code"] = status_code
        self.response["headers"] = headers
        self.response["mimetype"] = self.mimetype
        self.response["charset"] = self.charset

    def on_response_body(self, body: bytes) -> None:
        self.response["body"] = body


class AzureFunctionMiddleware(ServerlessMiddleware):
    """
    A middleware that wraps an ASGI application and handles transforming an incoming
    Azure Function request into the ASGI connection scope.

    After building the connection scope, it runs the ASGI application cycle and then
    serializes the response into an `HttpResponse`.
    """

    def asgi(self, event: HttpRequest) -> dict:
        server = None
        client = None
        scheme = "https"
        method = event.method
        headers = event.headers.items()
        parsed = urllib.parse.urlparse(event.url)
        scheme = parsed.scheme
        path = parsed.path
        query_string = encode_query_string(event.params) if event.params else ""

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

        body = event.get_body() or b""

        response = AzureFunctionCycle(scope, body=body)(self.app)
        return HttpResponse(
            body=response["body"],
            headers=response["headers"],
            status_code=response["status_code"],
            mimetype=response["mimetype"],
            charset=response["charset"],
        )
