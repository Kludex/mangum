import base64
import urllib.parse
from typing import Dict, Any

from .abstract_handler import AbstractHandler
from ..response import Response
from ..scope import Scope


class AwsCfLambdaAtEdge(AbstractHandler):
    """
    Handles AWS Elastic Load Balancer, really Application Load Balancer events transforming them into ASGI Scope
    and handling responses

    See: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-event-structure.html
    """

    TYPE = "AWS_CF_LAMBDA_AT_EDGE"

    @property
    def scope(self) -> Scope:
        event = self.trigger_event

        cf_request = event["Records"][0]["cf"]["request"]

        scheme_header = cf_request["headers"].get("cloudfront-forwarded-proto", [{}])
        scheme = scheme_header[0].get("value", "https")

        host_header = cf_request["headers"].get("host", [{}])
        server_name = host_header[0].get("value", "mangum")
        if ":" not in server_name:
            forwarded_port_header = cf_request["headers"].get("x-forwarded-port", [{}])
            server_port = forwarded_port_header[0].get("value", 80)
        else:
            server_name, server_port = server_name.split(":")  # pragma: no cover
        server = (server_name, int(server_port))

        source_ip = cf_request["clientIp"]
        client = (source_ip, 0)

        return Scope(
            method=cf_request["method"],
            headers=[
                [k.encode(), v[0]["value"].encode()]
                for k, v in cf_request["headers"].items()
            ],
            path=cf_request["uri"],
            scheme=scheme,
            query_string=cf_request["querystring"].encode(),
            server=server,
            client=client,
            trigger_event=self.trigger_event,
            trigger_context=self.trigger_context,
            event_type=self.TYPE,
        )

    @property
    def body(self) -> bytes:
        request = self.trigger_event["Records"][0]["cf"]["request"]
        body = request.get("body", {}).get("data", None)
        if request.get("body", {}).get("encoding", "") == "base64":
            body = base64.b64decode(body)
        return body

    def transform_response(self, response: Response) -> Dict[str, Any]:
        headers, multi_value_headers = self._handle_multi_value_headers(
            response.headers
        )

        body, is_base64_encoded = self._handle_base64_response_body(
            response.body, headers
        )

        headers = {
            key.decode().lower(): [{"key": key.decode().lower(), "value": val}]
            for key, val in response.headers
        }
        return {
            "status": response.status,
            "headers": headers,
            "body": body,
            "isBase64Encoded": is_base64_encoded,
        }
