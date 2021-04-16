import base64
import urllib.parse
from typing import Dict, Any

from .abstract_handler import AbstractHandler
from .. import Response, Request


class AwsHttpGateway(AbstractHandler):
    """
    Handles AWS HTTP Gateway events (v1.0 and v2.0), transforming them into ASGI Scope
    and handling responses

    See: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html  # noqa: E501
    """

    TYPE = "AWS_HTTP_GATEWAY"

    @property
    def event_version(self) -> str:
        return self.trigger_event.get("version", "")

    @property
    def request(self) -> Request:
        event = self.trigger_event

        headers = {}
        if event.get("headers"):
            headers = {k.lower(): v for k, v in event.get("headers", {}).items()}

        request_context = event["requestContext"]

        # API Gateway v2
        if self.event_version == "2.0":
            source_ip = request_context["http"]["sourceIp"]
            path = request_context["http"]["path"]
            http_method = request_context["http"]["method"]
            query_string = event.get("rawQueryString", "").encode()

            if event.get("cookies"):
                headers["cookie"] = "; ".join(event.get("cookies", []))

        # API Gateway v1
        elif self.event_version == "1.0":
            # v1.0 of the HTTP Gateway supports multiValueHeaders
            if event.get("multiValueHeaders"):
                headers.update(
                    {
                        k.lower(): ", ".join(v) if isinstance(v, list) else ""
                        for k, v in event.get("multiValueHeaders", {}).items()
                    }
                )

            source_ip = request_context.get("identity", {}).get("sourceIp")

            path = event["path"]
            http_method = event["httpMethod"]

            # AWS Blog Post on this:
            # https://aws.amazon.com/blogs/compute/support-for-multi-value-parameters-in-amazon-api-gateway/  # noqa: E501
            # A multi value param will be in multi value _and_ regular
            # queryStringParameters. Multi value takes precedence.
            if event.get("multiValueQueryStringParameters", False):
                query_string = urllib.parse.urlencode(
                    event.get("multiValueQueryStringParameters", {}), doseq=True
                ).encode()
            elif event.get("queryStringParameters", False):
                query_string = urllib.parse.urlencode(
                    event.get("queryStringParameters", {})
                ).encode()
            else:
                query_string = b""
        else:
            raise RuntimeError(
                "Unsupported version of HTTP Gateway Spec, only v1.0 and v2.0 are "
                "supported."
            )

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
        body = self.trigger_event.get("body", b"") or b""

        if self.trigger_event.get("isBase64Encoded", False):
            return base64.b64decode(body)
        if not isinstance(body, bytes):
            body = body.encode()

        return body

    def transform_response(self, response: Response) -> Dict[str, Any]:
        """
        This handles some unnecessary magic from AWS

        >  API Gateway can infer the response format for you
        Boooooo

        https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html#http-api-develop-integrations-lambda.response
        """
        headers, multi_value_headers = self._handle_multi_value_headers(
            response.headers
        )

        if self.event_version == "1.0":
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
        elif self.event_version == "2.0":
            # The API Gateway will infer stuff for us, but we'll just do that inference
            # here and keep the output consistent
            if "content-type" not in headers and response.body is not None:
                headers["content-type"] = "application/json"

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
        raise RuntimeError(  # pragma: no cover
            "Misconfigured event unable to return value, unsupported version."
        )
