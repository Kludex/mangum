import base64
from urllib.parse import urlencode, unquote, unquote_plus
from typing import Any, Dict, Generator, List, Tuple
from itertools import islice

from mangum.types import QueryParams

from .abstract_handler import AbstractHandler
from .. import Response, Request


def all_casings(input_string: str) -> Generator[str, None, None]:
    """
    Permute all casings of a given string.
    A pretty algoritm, via @Amber
    http://stackoverflow.com/questions/6792803/finding-all-possible-case-permutations-in-python
    """
    if not input_string:
        yield ""
    else:
        first = input_string[:1]
        if first.lower() == first.upper():
            for sub_casing in all_casings(input_string[1:]):
                yield first + sub_casing
        else:
            for sub_casing in all_casings(input_string[1:]):
                yield first.lower() + sub_casing
                yield first.upper() + sub_casing


def case_mutated_headers(multi_value_headers: Dict[str, List[str]]) -> Dict[str, str]:
    """Create str/str key/value headers, with duplicate keys case mutated."""
    headers: Dict[str, str] = {}
    for key, values in multi_value_headers.items():
        if len(values) > 0:
            casings = list(islice(all_casings(key), len(values)))
            for value, cased_key in zip(values, casings):
                headers[cased_key] = value
    return headers


class AwsAlb(AbstractHandler):
    """
    Handles AWS Elastic Load Balancer, really Application Load Balancer events
    transforming them into ASGI Scope and handling responses

    See:
        1. https://docs.aws.amazon.com/lambda/latest/dg/services-alb.html
        2. https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html  # noqa: E501
    """

    TYPE = "AWS_ALB"

    def _encode_query_string(self) -> bytes:
        """
        Encodes the queryStringParameters.
        The parameters must be decoded, and then encoded again to prevent double
        encoding.

        https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html  # noqa: E501
        "If the query parameters are URL-encoded, the load balancer does not decode
        them. You must decode them in your Lambda function."

        Issue: https://github.com/jordaneremieff/mangum/issues/178
        """

        params: QueryParams = self.trigger_event.get(
            "multiValueQueryStringParameters", {}
        )
        if not params:
            params = self.trigger_event.get("queryStringParameters", {})
        if not params:
            return b""
        params = {
            unquote_plus(key): unquote_plus(value)
            if isinstance(value, str)
            else tuple(unquote_plus(element) for element in value)
            for key, value in params.items()
        }
        return urlencode(params, doseq=True).encode()

    def transform_headers(self) -> List[Tuple[bytes, bytes]]:
        """Convert headers to a list of two-tuples per ASGI spec.

        Only one of `multiValueHeaders` or `headers` should be defined in the
        trigger event. However, we act as though they both might exist and pull
        headers out of both.
        """
        headers: List[Tuple[bytes, bytes]] = []
        if "multiValueHeaders" in self.trigger_event:
            for k, v in self.trigger_event["multiValueHeaders"].items():
                for inner_v in v:
                    headers.append((k.lower().encode(), inner_v.encode()))
        else:
            for k, v in self.trigger_event["headers"].items():
                headers.append((k.lower().encode(), v.encode()))
        return headers

    @property
    def request(self) -> Request:
        event = self.trigger_event

        headers = self.transform_headers()
        list_headers = [list(x) for x in headers]
        # Unique headers. If there are duplicates, it will use the last defined.
        uq_headers = {k.decode(): v.decode() for k, v in headers}

        source_ip = uq_headers.get("x-forwarded-for", "")
        path = unquote(event["path"]) if event["path"] else "/"
        http_method = event["httpMethod"]
        query_string = self._encode_query_string()

        server_name = uq_headers.get("host", "mangum")
        if ":" not in server_name:
            server_port = uq_headers.get("x-forwarded-port", 80)
        else:
            server_name, server_port = server_name.split(":")  # pragma: no cover
        server = (server_name, int(server_port))
        client = (source_ip, 0)

        return Request(
            method=http_method,
            headers=list_headers,
            path=path,
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

        headers = case_mutated_headers(multi_value_headers)

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
        #  https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html
        multi_value_headers_enabled = "multiValueHeaders" in self.trigger_event
        if multi_value_headers_enabled:
            out["multiValueHeaders"] = multi_value_headers
        else:
            out["headers"] = headers

        return out
