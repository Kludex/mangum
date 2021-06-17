from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING
import base64


from ..backends import WebSocket
from ..types import Response, WsRequest
from .abstract_handler import AbstractHandler

if TYPE_CHECKING:  # pragma: no cover
    from awslambdaric.lambda_context import LambdaContext


def get_server_and_headers(event: dict) -> Tuple:  # pragma: no cover
    if event.get("multiValueHeaders"):
        headers = {
            k.lower(): ", ".join(v) if isinstance(v, list) else ""
            for k, v in event.get("multiValueHeaders", {}).items()
        }
    elif event.get("headers"):
        headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    else:
        headers = {}

    # Subprotocols are not supported, so drop Sec-WebSocket-Protocol to be safe
    headers.pop("sec-websocket-protocol", None)

    server_name = headers.get("host", "mangum")
    if ":" not in server_name:
        server_port = headers.get("x-forwarded-port", 80)
    else:
        server_name, server_port = server_name.split(":")
    server = (server_name, int(server_port))

    return server, headers


class AwsWsGateway(AbstractHandler):
    """
    Handles AWS API Gateway Websocket events, transforming them into ASGI Scope and handling
    responses

    See: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
    """

    TYPE = "AWS_WS_GATEWAY"

    def __init__(
        self,
        trigger_event: Dict[str, Any],
        trigger_context: "LambdaContext",
        dsn: str,
        api_gateway_endpoint_url: Optional[str] = None,
        api_gateway_region_name: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ):
        super().__init__(trigger_event, trigger_context, **kwargs)
        request_context = trigger_event["requestContext"]
        connection_id = request_context["connectionId"]

        if api_gateway_endpoint_url is None:
            domain = request_context["domainName"]
            stage = request_context["stage"]
            api_gateway_endpoint_url = (
                f"https://{domain}/{stage}/@connections/{connection_id}"
            )

        self.message_type = request_context["eventType"]
        self.websocket = WebSocket(
            dsn=dsn,
            connection_id=connection_id,
            api_gateway_endpoint_url=api_gateway_endpoint_url,
            api_gateway_region_name=api_gateway_region_name,
        )

    @property
    def request(self) -> WsRequest:
        request_context = self.trigger_event["requestContext"]
        server, headers = get_server_and_headers(self.trigger_event)
        source_ip = request_context.get("identity", {}).get("sourceIp")
        client = (source_ip, 0)
        headers_list = [[k.encode(), v.encode()] for k, v in headers.items()]

        return WsRequest(
            headers=headers_list,
            path="/",
            scheme=headers.get("x-forwarded-proto", "wss"),
            query_string=b"",
            server=server,
            client=client,
            trigger_event=self.trigger_event,
            trigger_context=self.trigger_context,
            event_type=self.TYPE,
        )

    @property
    def body(self) -> bytes:
        # API Gateway WebSocket APIs don't currently support binary frames in incoming message payloads.
        # https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-api-develop-binary-media-types.html

        body = self.trigger_event.get("body", b"") or b""

        if self.trigger_event.get("isBase64Encoded", False):
            return base64.b64decode(body)
        if not isinstance(body, bytes):
            body = body.encode()

        return body

    def transform_response(self, response: Response) -> Dict[str, Any]:
        return {"statusCode": response.status}
