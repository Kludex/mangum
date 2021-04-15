import base64
import urllib.parse
from typing import Dict, Any

from .abstract_handler import AbstractHandler
from .. import Response, Request


class AwsAlb(AbstractHandler):
    """
    Handles AWS Elastic Load Balancer, really Application Load Balancer events
    transforming them into ASGI Scope and handling responses

    See: https://docs.aws.amazon.com/lambda/latest/dg/services-alb.html
    """

    TYPE = "AWS_ALB"

    @property
    def request(self) -> Request:
        event = self.trigger_event

        headers = {}
        if event.get("headers"):
            headers = {k.lower(): v for k, v in event.get("headers", {}).items()}

        source_ip = headers.get("x-forwarded-for", "")
        path = event["path"]
        http_method = event["httpMethod"]
        query_string = urllib.parse.urlencode(
            event.get("queryStringParameters", {}), doseq=True
        ).encode()

        server_name = headers.get("host", "mangum")
        if ":" not in server_name:
            server_port = headers.get("x-forwarded-port", 80)
        else:
            server_name, server_port = server_name.split(":")  # pragma: no cover
        server = (server_name, int(server_port))
        client = (source_ip, 0)

        if not path:
            path = "/"

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
        body = self.trigger_event.get("body", b"")

        if not body:
            body = b""
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
