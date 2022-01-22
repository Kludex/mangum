import base64
import urllib.parse
from typing import Dict, Any, List, Tuple

from . import AwsApiGateway
from .. import Response, Request


class AwsHttpGateway(AwsApiGateway):
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
            query_string = self._encode_query_string()
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
        else:
            path = self._strip_base_path(path)

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
        if self.event_version == "1.0":
            return self.transform_response_v1(response)
        elif self.event_version == "2.0":
            return self.transform_response_v2(response)
        raise RuntimeError(  # pragma: no cover
            "Misconfigured event unable to return value, unsupported version."
        )

    def transform_response_v1(self, response: Response) -> Dict[str, Any]:
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

    def _combine_headers_v2(
        self, input_headers: List[List[bytes]]
    ) -> Tuple[Dict[str, str], List[str]]:
        output_headers: Dict[str, str] = {}
        cookies: List[str] = []
        for key, value in input_headers:
            normalized_key: str = key.decode().lower()
            normalized_value: str = value.decode()
            if normalized_key == "set-cookie":
                cookies.append(normalized_value)
            else:
                if normalized_key in output_headers:
                    normalized_value = (
                        f"{output_headers[normalized_key]},{normalized_value}"
                    )
                output_headers[normalized_key] = normalized_value
        return output_headers, cookies

    def transform_response_v2(self, response_in: Response) -> Dict[str, Any]:
        # The API Gateway will infer stuff for us, but we'll just do that inference
        # here and keep the output consistent

        headers, cookies = self._combine_headers_v2(response_in.headers)

        if "content-type" not in headers and response_in.body is not None:
            headers["content-type"] = "application/json"

        body, is_base64_encoded = self._handle_base64_response_body(
            response_in.body, headers
        )
        response_out = {
            "statusCode": response_in.status,
            "body": body,
            "headers": headers or None,
            "cookies": cookies or None,
            "isBase64Encoded": is_base64_encoded,
        }
        return {key: value for key, value in response_out.items() if value is not None}
