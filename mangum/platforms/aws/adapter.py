import base64
from mangum.utils import encode_query_string, maybe_encode
from mangum.asgi.protocol import ASGICycle
from mangum.asgi.adapter import ServerlessAdapter


class AWSLambdaASGICycle(ASGICycle):
    """
    An adapter that handles the HTTP request-response cycle for an ASGI application and
    builds a valid response to return to AWS Lambda & API Gateway.

    The response is a Python dictionary with the following structure:

        {
            "statusCode": int,
            "isBase64Encoded": bool,
            "headers": dict,
            "body": str,
        }
    """

    def __init__(self, *args, **kwargs) -> None:
        self.binary = kwargs.pop("binary", False)
        super().__init__(*args, **kwargs)

    def on_response_start(self, headers: dict, status_code: int) -> None:
        self.response["statusCode"] = status_code
        self.response["isBase64Encoded"] = self.binary
        self.response["headers"] = {k.decode(): v.decode() for k, v in headers.items()}

    def on_response_close(self) -> None:
        if self.binary:
            body = base64.b64encode(self.body)
        else:
            body = self.body.decode()
        self.response["body"] = body


class AWSLambdaAdapter(ServerlessAdapter):
    """
    A adapter that wraps an ASGI application and handles transforming an incoming
    AWS Lambda & API Gateway request into the ASGI connection scope.

    After building the connection scope, it runs the ASGI application cycle and returns
    the response.
    """

    def asgi(self, event: dict, context: dict) -> dict:

        method = event["httpMethod"]
        headers = event["headers"] or {}
        path = event["path"]
        scheme = headers.get("X-Forwarded-Proto", "http")
        query_string_params = event["queryStringParameters"]
        query_string = (
            encode_query_string(query_string_params) if query_string_params else b""
        )

        client_addr = event["requestContext"].get("identity", {}).get("sourceIp", None)
        client = (client_addr, 0)  # TODO: Client port

        server_addr = headers["Host"]
        if ":" not in server_addr:
            server_port = 80
        else:
            server_port = int(server_addr.split(":")[1])

        server = (server_addr, server_port)

        scope = {
            "server": server,
            "client": client,
            "scheme": scheme,
            "root_path": "",
            "query_string": query_string,
            "headers": [[maybe_encode(k), maybe_encode(v)] for k, v in headers.items()],
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
        }

        binary = event.get("isBase64Encoded", False)
        body = event["body"]
        if body:
            if binary:
                body = base64.b64decode(body)

            else:
                body = maybe_encode(body)
        else:
            body = b""

        response = AWSLambdaASGICycle(scope, binary=binary)(self.app, body=body)
        return response

    def _debug(self, content: str, status_code: int = 500) -> None:
        return {
            "statusCode": status_code,
            "isBase64Encoded": False,
            "headers": {"content-type": "text/plain; charset=utf-8"},
            "body": content,
        }
