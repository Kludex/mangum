import base64
import urllib.parse
from typing import Dict, Any, List, Tuple

from .abstract_handler import AbstractHandler
from .. import Response, Request


class AwsAlb(AbstractHandler):
    """
    Handles AWS Elastic Load Balancer, really Application Load Balancer events
    transforming them into ASGI Scope and handling responses

    See:
        1. https://docs.aws.amazon.com/lambda/latest/dg/services-alb.html
        2. https://docs.aws.amazon.com/elasticloadbalancing/latest/application/
           lambda-functions.html
    """

    TYPE = "AWS_ALB"

    def encode_query_string(self) -> bytes:
        """
        Encodes the queryStringParameters.

        The parameters must be decoded, and then encoded again to prevent double
        encoding.

        See: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/
             lambda-functions.html
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

        return urllib.parse.urlencode(query).encode()

    def transform_headers(self) -> List[Tuple[bytes, bytes]]:
        """Convert headers to a list of two-tuples per ASGI spec.

        Only one of `multiValueHeaders` or `headers` should be defined in the
        trigger event.
        """
        headers = []
        if self.trigger_event.get("multiValueHeaders"):
            for k, v in self.trigger_event.get("multiValueHeaders", {}).items():
                for inner_v in v:
                    headers.append((k.lower().encode(), inner_v.encode()))
        elif self.trigger_event.get("headers"):
            for k, v in self.trigger_event.get("headers", {}).items():
                headers.append((k.lower().encode(), v.encode()))
        return headers

    @property
    def request(self) -> Request:
        event = self.trigger_event

        headers = self.transform_headers()
        # Unique headers. If there are duplicates, it will use the last defined.
        uq_headers = {k.decode(): v.decode() for k, v in headers}

        source_ip = uq_headers.get("x-forwarded-for", "")
        path = event["path"]
        http_method = event["httpMethod"]
        query_string = self.encode_query_string()

        server_name = uq_headers.get("host", "mangum")
        if ":" not in server_name:
            server_port = uq_headers.get("x-forwarded-port", 80)
        else:
            server_name, server_port = server_name.split(":")  # pragma: no cover
        server = (server_name, int(server_port))
        client = (source_ip, 0)

        if not path:
            path = "/"

        return Request(
            method=http_method,
            headers=[list(x) for x in headers],
            path=urllib.parse.unquote(path),
            scheme=uq_headers.get("x-forwarded-proto", "https"),
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

        multi_value_headers: Dict[str, List[str]] = {}
        for key, value in response.headers:
            lower_key = key.decode().lower()
            if lower_key not in multi_value_headers:
                multi_value_headers[lower_key] = []
            multi_value_headers[lower_key].append(value.decode())
        headers: Dict[str, str] = {k: v[-1] for k, v in multi_value_headers.items()}

        body, is_base64_encoded = self._handle_base64_response_body(
            response.body, headers
        )

        out = {
            "statusCode": response.status,
            "body": body,
            "isBase64Encoded": is_base64_encoded,
        }

        #  "You must use multiValueHeaders if you have enabled multi-value headers
        #  and headers otherwise"
        #  https://docs.aws.amazon.com/elasticloadbalancing/latest/application/
        #  lambda-functions.html
        multi_value_headers_enabled = "multiValueHeaders" in self.trigger_event
        if multi_value_headers_enabled:
            out["multiValueHeaders"] = multi_value_headers
        else:
            out["headers"] = headers

        return out
