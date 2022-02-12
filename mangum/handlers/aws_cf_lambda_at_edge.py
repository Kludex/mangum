import base64
from typing import Dict, Any, List

from .abstract_handler import AbstractHandler
from .. import Response, Request


class AwsCfLambdaAtEdge(AbstractHandler):
    @property
    def request(self) -> Request:
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

        return Request(
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
        )

    @property
    def body(self) -> bytes:
        request = self.trigger_event["Records"][0]["cf"]["request"]
        body = request.get("body", {}).get("data", None) or b""

        if request.get("body", {}).get("encoding", "") == "base64":
            return base64.b64decode(body)
        if not isinstance(body, bytes):
            body = body.encode()

        return body

    def transform_response(self, response: Response) -> Dict[str, Any]:
        headers_dict, _ = self._handle_multi_value_headers(response.headers)
        body, is_base64_encoded = self._handle_base64_response_body(
            response.body, headers_dict
        )

        # Expand headers to weird list of Dict[str, List[Dict[str, str]]]
        headers_expanded: Dict[str, List[Dict[str, str]]] = {
            key.decode().lower(): [{"key": key.decode().lower(), "value": val.decode()}]
            for key, val in response.headers
        }
        return {
            "status": response.status,
            "headers": headers_expanded,
            "body": body,
            "isBase64Encoded": is_base64_encoded,
        }
