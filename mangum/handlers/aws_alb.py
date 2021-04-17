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

    def encode_query_string(self) -> bytes:
        """
        Encodes the queryStringParameters.

        The parameters must be decoded, and then encoded again to prevent double
        encoding.

        See: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html
        "If the query parameters are URL-encoded, the load balancer does not decode
        them. You must decode them in your Lambda function."

        Issue: https://github.com/jordaneremieff/mangum/issues/178
        """

        params = self.trigger_event.get("multiValueQueryStringParameters")
        if not params:
            params = self.trigger_event.get("queryStringParameters")
        if not params:
            return b""  # No query parameters, exit early with an empty byte string.

        # Loop through the query parameters, unquote each key and value and append the
        # pair as a tuple to the query list. If value is a list or a tuple, loop
        # through the nested struture and unqote.
        query = []
        for key, value in params.items():
            if isinstance(value, (tuple, list)):
                for v in value:
                    query.append(
                        (urllib.parse.unquote_plus(key), urllib.parse.unquote_plus(v))
                    )
            else:
                query.append(
                    (urllib.parse.unquote_plus(key), urllib.parse.unquote_plus(value))
                )

        return urllib.parse.urlencode(query, quote_via=urllib.parse.quote_plus).encode()

    @property
    def request(self) -> Request:
        event = self.trigger_event

        headers = {}
        if event.get("headers"):
            headers = {k.lower(): v for k, v in event.get("headers", {}).items()}

        source_ip = headers.get("x-forwarded-for", "")
        path = event["path"]
        http_method = event["httpMethod"]
        query_string = self.encode_query_string()

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
        if self.trigger_event.get("isBase64Encoded", False):
            body = base64.b64decode(body)
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
