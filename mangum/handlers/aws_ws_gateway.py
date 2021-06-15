from typing import Any, Dict, Tuple


from mangum.backends import WebSocket
from .abstract_handler import AbstractHandler
from .. import Response, Request


def get_server_and_headers(event: dict) -> Tuple:  # pragma: no cover
    # TODO multi value headers
    headers = (
        {k.lower(): v for k, v in event.get("headers").items()}  # type: ignore
        if event.get("headers")
        else {}
    )

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
    https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-api-develop-routes.html
    https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-mapping-template-reference.html
    https://docs.aws.amazon.com/code-samples/latest/catalog/python-apigateway-websocket-lambda_chat.py.html
    """

    TYPE = "AWS_WS_GATEWAY"

    def __init__(
        self,
        trigger_event: Dict[str, Any],
        trigger_context: "LambdaContext",
        **kwargs: Dict[str, Any],
    ):
        super().__init__(trigger_event, trigger_context, **kwargs)

        # https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-how-to-call-websocket-api-connections.html
        request_context = trigger_event["requestContext"]
        connection_id = request_context["connectionId"]
        domain = request_context["domainName"]
        stage = request_context["stage"]
        api_gateway_endpoint_url = (
            f"https://{domain}/{stage}/@connections/{connection_id}"
        )

        self.websocket = WebSocket(
            **{
                **kwargs,
                "connection_id": connection_id,
                "api_gateway_endpoint_url": api_gateway_endpoint_url,
            }
        )
        self.message_type = request_context["eventType"]

    # TODO
    @property
    def request(self) -> Request:
        request_context = self.trigger_event["requestContext"]
        server, headers = get_server_and_headers(self.trigger_event)
        source_ip = request_context.get("identity", {}).get("sourceIp")
        client = (source_ip, 0)
        headers_list = [[k.encode(), v.encode()] for k, v in headers.items()]

        return Request(
            type="websocket",
            method="GET",  # TODO don't exist in websocket's scope
            headers=headers_list,
            path="/",
            scheme=headers.get("x-forwarded-proto", "wss"),
            query_string=b"",
            server=server,
            client=client,
            # TODO subprotocols
            # https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-connect-route-subprotocol.html
            trigger_event=self.trigger_event,
            trigger_context=self.trigger_context,
            event_type=self.TYPE,
        )

    @property
    def body(self) -> bytes:
        # TODO binary payloads support ?
        # https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-api-develop-binary-media-types.html
        body = self.trigger_event.get("body", "")
        return body.encode()

    def transform_response(self, response: Response) -> Dict[str, Any]:
        return {"statusCode": response.status}
