import asyncio
import logging
from typing import Optional, Any, Dict, Tuple
import json
import os
import hashlib
import hmac
import datetime
from functools import partial
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None

from mangum.exceptions import WebSocketError, ConfigurationError
from mangum.types import Scope

from .abstract_handler import AbstractHandler
from .. import Response, Request


def sign(key: bytes, msg: str) -> str:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def get_sigv4_headers(body: str, region_name: str) -> dict:
    now = datetime.datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    request_date = now.strftime("%Y%m%d")
    host = f"apigatewaymanagementapi.{region_name}.amazonaws.com"
    canonical_headers = f"host:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(body).hexdigest()
    canonical_request = (
        f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    service = "apigatewaymanagementapi"
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{request_date}/{region_name}/{service}/aws4_request"
    request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
    string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{request_hash}"
    access_key = os.environ["AWS_ACCESS_KEY_ID"]
    secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]
    key_date = sign(f"AWS4{secret_key}".encode(), request_date)
    key_region = sign(key_date, region_name)
    key_service = sign(key_region, service)
    signing_key = sign(key_service, "aws4_request")
    signature = hmac.new(
        signing_key, (string_to_sign).encode(), hashlib.sha256
    ).hexdigest()
    authorization_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Content-Type": "application/x-amz-json-1.0",
        "X-Amz-Date": amz_date,
        "Authorization": authorization_header,
    }

    return headers


def get_server_and_headers(event: dict) -> Tuple:  # pragma: no cover
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

    See: https://docs.aws.amazon.com/code-samples/latest/catalog/python-apigateway-websocket-lambda_chat.py.html
    https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-api-develop-routes.html
    https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-mapping-template-reference.html
    https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
    """

    TYPE = "AWS_WS_GATEWAY"

    # dsn: InitVar[str]
    # connection_id: str
    # api_gateway_endpoint_url: str
    # api_gateway_region_name: str
    # broadcast: bool

    def __init__(
        self,
        trigger_event: Dict[str, Any],
        trigger_context: "LambdaContext",
        dsn: Optional[str] = None,
        api_gateway_endpoint_url: Optional[str] = None,
        api_gateway_region_name: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ):
        super().__init__(trigger_event, trigger_context, **kwargs)

        self.dsn = dsn
        self.api_gateway_endpoint_url = api_gateway_endpoint_url
        self.api_gateway_region_name = api_gateway_region_name

        if httpx is None:  # pragma: no cover
            raise WebSocketError("httpx must be installed to use WebSockets.")

        self.logger: logging.Logger = logging.getLogger("mangum.websocket")
        parsed_dsn = urlparse(dsn)
        if not any((parsed_dsn.hostname, parsed_dsn.path)):
            raise ConfigurationError("Invalid value for `dsn` provided.")

        scheme = parsed_dsn.scheme
        self.logger.debug(
            f"Attempting WebSocket backend connection using scheme: {scheme}"
        )

        if scheme == "sqlite":
            self.logger.info(
                "The `SQLiteBackend` should be only be used for local "
                "debugging. It will not work in a deployed environment."
            )
            # TODO commented because I couldn't find it
            # from mangum.backends.sqlite import SQLiteBackend

            # self._backend = SQLiteBackend(dsn)  # type: ignore

        elif scheme == "dynamodb":
            from mangum.backends.dynamodb import DynamoDBBackend

            self._backend = DynamoDBBackend(dsn)  # type: ignore

        elif scheme == "s3":
            from mangum.backends.s3 import S3Backend

            self._backend = S3Backend(dsn)  # type: ignore

        elif scheme in ("postgresql", "postgres"):
            from mangum.backends.postgresql import PostgreSQLBackend

            self._backend = PostgreSQLBackend(dsn)  # type: ignore

        elif scheme == "redis":
            from mangum.backends.redis import RedisBackend

            self._backend = RedisBackend(dsn)  # type: ignore

        else:
            raise ConfigurationError(f"{scheme} does not match a supported backend.")
        self.logger.info("WebSocket backend connection established.")

    # TODO
    @property
    def request(self) -> Request:
        event = self.trigger_event
        request_context = event["requestContext"]
        event_type = request_context.get("eventType")
        # route_key = event.get("requestContext", {}).get("routeKey")
        # if route_key == "$connect":

        if event_type == "CONNECT":
            server, headers = get_server_and_headers(event)
            source_ip = request_context.get("identity", {}).get("sourceIp")
            client = (source_ip, 0)
            initial_scope = {
                "type": "websocket",
                "path": "/",
                "headers": headers,
                "raw_path": None,
                "root_path": "",
                "scheme": headers.get("x-forwarded-proto", "wss"),
                "query_string": "",
                "server": server,
                "client": client,
                "asgi": {"version": "3.0"},
                "aws.events": {"connect": event, "message": {}},
            }
            # if self.config.broadcast:
            #    initial_scope["aws.subscriptions"] = []
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.on_connect(initial_scope))

            return Request(
                method="GET",  # TODO don't exist in websocket's scope
                headers=headers,
                path="/",
                scheme=headers.get("x-forwarded-proto", "wss"),
                query_string=b"",
                server=server,
                client=client,
                trigger_event=self.trigger_event,
                trigger_context=self.trigger_context,
                event_type=self.TYPE,
            )
        elif event_type == "MESSAGE":
            body = event.get("body", "")
            asgi_cycle = WebSocketCycle(body, websocket=websocket)
            response = asgi_cycle(self.app, request_context=request_context)

            return response
        elif event_type == "DISCONNECT":
            loop = asyncio.get_event_loop()
            loop.run_until_complete(websocket.on_disconnect())

        raise RuntimeError(f"Unknown eventType: {event_type}")

    # TODO
    @property
    def body(self) -> bytes:
        pass

    # TODO
    def transform_response(self, response: Response) -> Dict[str, Any]:
        pass

    async def load_scope(self, request_context: dict = None) -> Optional[Scope]:
        scope = await self._backend.retrieve(self.connection_id)
        if scope:
            scope = json.loads(scope)
            if request_context:
                message_events = scope["aws.events"]["message"]
                if message_events:
                    order_id = list(message_events.keys())[-1]
                else:
                    order_id = 0
                scope["aws.events"]["message"][order_id] = request_context
            scope.update(
                {
                    "query_string": scope["query_string"].encode(),
                    "headers": [
                        [k.encode(), v.encode()] for k, v in scope["headers"].items()
                    ],
                }
            )
        else:
            scope = None

        return scope

    async def save_scope(self, scope: dict, decode: bool = True) -> None:
        if decode:
            scope.update(
                {
                    "query_string": scope["query_string"].decode(),
                    "headers": {h[0].decode(): h[1].decode() for h in scope["headers"]},
                }
            )
        scope = json.dumps(scope)
        await self._backend.save(self.connection_id, json_scope=scope)

    async def on_connect(self, initial_scope: dict) -> None:
        await self._backend.connect()
        self.logger.debug("Creating scope entry for %s", self.connection_id)
        await self.save_scope(initial_scope, decode=False)

    async def on_message(self, request_context: dict) -> Scope:
        await self._backend.connect()
        self.logger.debug("Retrieving scope entry for %s", self.connection_id)
        return await self.load_scope(request_context=request_context)

    async def on_disconnect(self) -> None:
        await self._backend.connect()
        self.logger.debug("Deleting scope entry for %s", self.connection_id)

        if self.broadcast:
            scope = await self.load_scope()
            if scope:
                subscriptions = scope["aws.subscriptions"]
                if subscriptions:
                    for channel in subscriptions:
                        await self._backend.unsubscribe(
                            channel, connection_id=self.connection_id
                        )

        await self._backend.delete(self.connection_id)

    async def publish(self, channel: str, *, body: bytes) -> None:
        subscribers = await self._backend.get_subscribers(channel)
        tasks = []
        async with httpx.AsyncClient() as client:
            for connection_id in subscribers:
                if isinstance(connection_id, bytes):
                    connection_id = connection_id.decode()

                task = asyncio.create_task(
                    self._post_to_connection(
                        connection_id, client=client, body=body, channel=channel
                    )
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

    async def subscribe(self, channel: str, *, scope: Scope) -> None:
        await self._backend.subscribe(channel, connection_id=self.connection_id)
        scope["aws.subscriptions"].append(channel)
        await self.save_scope(scope)

    async def unsubscribe(self, channel: str, *, scope: Scope) -> None:
        await self._backend.unsubscribe(channel, connection_id=self.connection_id)
        scope["aws.subscriptions"].remove(channel)
        await self.save_scope(scope)

    async def post_to_connection(self, body: bytes) -> None:
        client = httpx.AsyncClient()
        await self._post_to_connection(
            connection_id=self.connection_id, client=client, body=body
        )

    async def delete_connection(self) -> None:
        async with httpx.AsyncClient() as client:
            url = f"{self.api_gateway_endpoint_url}/@connections/{self.connection_id}"
            await client.delete(url)

    async def _post_to_connection(
        self,
        connection_id: str = None,
        *,
        client,  #: httpx.AsyncClient, Commented because httpx may not be installed
        body: bytes,
        channel: Optional[str] = None,
    ) -> None:  # pragma: no cover
        loop = asyncio.get_event_loop()
        headers = await loop.run_in_executor(
            None, partial(get_sigv4_headers, body, self.api_gateway_region_name)
        )
        url = f"{self.api_gateway_endpoint_url}/@connections/{connection_id}"

        response = await client.post(url, data=body, headers=headers)
        if response.status_code == 410:
            if channel:
                self.logger.debug(
                    "Deleting scope entry for %s and unsubscribing from %s",
                    connection_id,
                    channel,
                )
                await self._backend.delete(connection_id)
                await self._backend.unsubscribe(channel, connection_id=connection_id)
            else:
                await self.on_disconnect()
        elif response.status_code != 200:
            raise WebSocketError(f"Error: {response.status_code}")
