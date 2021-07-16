import base64
import urllib.parse
from typing import Dict, Any, TYPE_CHECKING

from .abstract_handler import AbstractHandler
from .. import Response, Request


if TYPE_CHECKING:  # pragma: no cover
    from awslambdaric.lambda_context import LambdaContext


class AwsApiGateway(AbstractHandler):
    """
    Handles AWS API Gateway events, transforming them into ASGI Scope and handling
    responses

    See: https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html
    """

    TYPE = "AWS_API_GATEWAY"

    def __init__(
        self,
        trigger_event: Dict[str, Any],
        trigger_context: "LambdaContext",
        api_gateway_base_path: str = "/",
        **kwargs: Dict[str, Any],  # type: ignore
    ):
        super().__init__(trigger_event, trigger_context, **kwargs)
        self.api_gateway_base_path = api_gateway_base_path

    @property
    def request(self) -> Request:
        event = self.trigger_event

        # multiValue versions of headers take precedence over their plain versions
        # https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
        if event.get("multiValueHeaders"):
            headers = {
                k.lower(): ", ".join(v) if isinstance(v, list) else ""
                for k, v in event.get("multiValueHeaders", {}).items()
            }
        elif event.get("headers"):
            headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
        else:
            headers = {}

        request_context = event["requestContext"]

        source_ip = request_context.get("identity", {}).get("sourceIp")

        path = event["path"]
        http_method = event["httpMethod"]

        if event.get("multiValueQueryStringParameters"):
            query_string = urllib.parse.urlencode(
                event.get("multiValueQueryStringParameters", {}), doseq=True
            ).encode()
        elif event.get("queryStringParameters"):
            query_string = urllib.parse.urlencode(
                event.get("queryStringParameters", {})
            ).encode()
        else:
            query_string = b""

        server_name = headers.get("host", "mangum")
        if ":" not in server_name:
            server_port = headers.get("x-forwarded-port", 80)
        else:
            server_name, server_port = server_name.split(":")  # pragma: no cover
        server = (server_name, int(server_port))
        client = (source_ip, 0)

        if not path:
            path = "/"
        elif self.api_gateway_base_path and self.api_gateway_base_path != "/":
            if not self.api_gateway_base_path.startswith("/"):
                self.api_gateway_base_path = f"/{self.api_gateway_base_path}"
            if path.startswith(self.api_gateway_base_path):
                path = path[len(self.api_gateway_base_path) :]

        return Request(
            method=http_method,
            headers=[[k.encode(), v.encode()] for k, v in headers.items()],
            path=urllib.parse.unquote(path),
            scheme=headers.get("x-forwarded-proto", "https"),
            query_string=query_string,
            server=server,
            client=client,
            trigger_event=self.trigger_event,
            trigger_context=self.trigger_context,
            event_type=self.TYPE,
        )

    @property
    def body(self) -> bytes:
        body = self.trigger_event.get("body", b"") or b""

        if self.trigger_event.get("isBase64Encoded", False):
            return base64.b64decode(body)
        if not isinstance(body, bytes):
            body = body.encode()

        return body

    def transform_response(self, response: Response) -> Dict[str, Any]:
        headers, multi_value_headers = self._handle_multi_value_headers(
            response.headers
        )

        body, is_base64_encoded = self._handle_base64_response_body(
            response.body, headers
        )

        return {
            "statusCode": response.status,
            "headers": headers,
            "multiValueHeaders": multi_value_headers,
            "body": body,
            "isBase64Encoded": is_base64_encoded,
        }
