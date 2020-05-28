import logging
import typing
import os
import httpx
from dataclasses import dataclass, InitVar
from urllib.parse import urlparse

from mangum.types import Scope
from mangum.exceptions import WebSocketError, ConfigurationError

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover
    boto3 = None

try:
    import orjson
except ImportError:
    orjson = None

import hashlib
import hmac
import datetime


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_sigv4_headers(body, *, region_name):
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
    key_date = sign(("AWS4" + secret_key).encode(), request_date)
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


@dataclass
class WebSocket:

    connection_id: str
    dsn: InitVar[str]
    api_gateway_region_name: str
    api_gateway_endpoint_url: str
    scope_json: typing.Optional[str] = None
    api_gateway_client: typing.Optional[typing.Any] = None

    def __post_init__(self, dsn: str) -> None:
        if boto3 is None:  # pragma: no cover
            raise WebSocketError("boto3 must be installed to use WebSockets.")
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
            from mangum.backends.sqlite import SQLiteBackend

            self._backend = SQLiteBackend(dsn)  # type: ignore

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

        self.logger.debug("WebSocket backend connection established.")

    def load_scope(self) -> typing.Optional[Scope]:
        json_scope = self._backend.retrieve(self.connection_id)
        if not json_scope:
            scope = None
        else:
            scope = orjson.loads(json_scope)
            scope.update(
                {
                    "query_string": scope["query_string"].encode(),
                    "headers": [
                        [k.encode(), v.encode()] for k, v in scope["headers"].items()
                    ],
                }
            )

        return scope

    def save_scope(self, scope: dict, decode: bool = True) -> None:
        if decode:
            scope.update(
                {
                    "query_string": scope["query_string"].decode(),
                    "headers": {h[0].decode(): h[1].decode() for h in scope["headers"]},
                }
            )
        json_scope = orjson.dumps(scope)
        self._backend.save(self.connection_id, json_scope=json_scope)

    def on_connect(self, scope: dict) -> None:
        self.logger.debug("Creating scope entry for %s", self.connection_id)
        self.save_scope(scope, decode=False)

    def on_message(self, event: dict) -> Scope:
        self.logger.debug("Retrieving scope entry for %s", self.connection_id)
        scope = self.load_scope()
        scope["aws.events"].append(event)

        return scope

    def on_disconnect(self) -> None:
        self.logger.debug("Deleting scope entry for %s", self.connection_id)
        scope = self.load_scope()
        if scope:
            subscriptions = scope["websocket.broadcast"]["subscriptions"]
            if subscriptions:
                for channel in subscriptions:
                    self._backend.unsubscribe(self.connection_id, channel)

        self._backend.delete(self.connection_id)

    async def publish(self, channel: str, *, body: bytes, scope: Scope) -> None:
        subscribers = self._backend.get_subscribers(channel)
        for connection_id in subscribers:
            if isinstance(connection_id, bytes):
                connection_id = connection_id.decode()
            await self.post_to_connection(connection_id, body=body, channel=channel)
        self.save_scope(scope)

    async def subscribe(self, channel: str, *, scope: Scope) -> None:
        self._backend.subscribe(channel, connection_id=self.connection_id)
        scope["extensions"]["websocket.broadcast"]["subscriptions"].append(channel)
        self.save_scope(scope)

    async def unsubscribe(self, channel: str, *, scope: Scope) -> None:
        self._backend.unsubscribe(channel, connection_id=self.connection_id)
        scope["extensions"]["websocket.broadcast"]["subscriptions"].remove(channel)
        self.save_scope(scope)

    async def send(self, body: bytes) -> None:
        await self.post_to_connection(self.connection_id, body=body)

    async def post_to_connection(
        self, connection_id: str, *, body: bytes, channel: typing.Optional[str] = None
    ) -> None:  # pragma: no cover

        headers = get_sigv4_headers(body, region_name=self.api_gateway_region_name)
        url = f"{self.api_gateway_endpoint_url}/@connections/{connection_id}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=body, headers=headers)

        if response.status_code == 410:
            if channel:
                self.logger.debug(
                    "Deleting scope entry for %s and unsubscribing from %s",
                    connection_id,
                    channel,
                )
                self._backend.delete(connection_id)
                self._backend.unsubscribe(channel, connection_id=connection_id)
            else:
                self.on_disconnect()

        # if self.api_gateway_client is None:
        #     self.api_gateway_client = boto3.client(
        #         "apigatewaymanagementapi",
        #         endpoint_url=self.api_gateway_endpoint_url,
        #         region_name=self.api_gateway_region_name,
        #     )

        # try:
        #     self.api_gateway_client.post_to_connection(
        #         ConnectionId=connection_id, Data=body
        #     )
        # except ClientError as exc:
        #     status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        #     if status_code == 410:
        #         if channel:
        #             self.logger.debug(
        #                 "Deleting scope entry for %s and unsubscribing from %s",
        #                 connection_id,
        #                 channel,
        #             )
        #             self._backend.delete(connection_id)
        #             self._backend.unsubscribe(channel, connection_id=connection_id)
        #         else:
        #             self.on_disconnect()
        #     else:
        #         raise WebSocketError(exc)
