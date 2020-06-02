import asyncio
import logging
import typing
import json
import os
import hashlib
import hmac
import datetime
from functools import partial
from dataclasses import dataclass
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None

from mangum.exceptions import WebSocketError, ConfigurationError
from mangum.types import Scope
from mangum.config import Config


def sign(key: bytes, msg: str):
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


@dataclass
class WebSocket:

    config: Config

    def __post_init__(self) -> None:
        if httpx is None:  # pragma: no cover
            raise WebSocketError("httpx must be installed to use WebSockets.")

        self.logger: logging.Logger = logging.getLogger("mangum.websocket")
        parsed_dsn = urlparse(self.config.dsn)
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

            self._backend = SQLiteBackend(self.config.dsn)  # type: ignore

        elif scheme == "dynamodb":
            from mangum.backends.dynamodb import DynamoDBBackend

            self._backend = DynamoDBBackend(self.config.dsn)  # type: ignore

        elif scheme == "s3":
            from mangum.backends.s3 import S3Backend

            self._backend = S3Backend(self.config.dsn)  # type: ignore

        elif scheme in ("postgresql", "postgres"):
            from mangum.backends.postgresql import PostgreSQLBackend

            self._backend = PostgreSQLBackend(self.config.dsn)  # type: ignore

        elif scheme == "redis":
            from mangum.backends.redis import RedisBackend

            self._backend = RedisBackend(self.config.dsn)  # type: ignore

        else:
            raise ConfigurationError(f"{scheme} does not match a supported backend.")
        self.logger.info("WebSocket backend connection established.")

    async def load_scope(self, event: dict = None) -> typing.Optional[Scope]:
        scope = await self._backend.retrieve(self.config.connection_id)
        if scope:
            scope = json.loads(scope)
            if event:
                scope["aws.events"].append(event)
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
        await self._backend.save(self.config.connection_id, json_scope=scope)

    async def on_connect(self, initial_scope: dict) -> None:
        await self._backend.connect()
        self.logger.debug("Creating scope entry for %s", self.config.connection_id)
        await self.save_scope(initial_scope, decode=False)

    async def on_message(self, event: dict) -> Scope:
        await self._backend.connect()
        self.logger.debug("Retrieving scope entry for %s", self.config.connection_id)
        return await self.load_scope(event=event)

    async def on_disconnect(self) -> None:
        await self._backend.connect()
        self.logger.debug("Deleting scope entry for %s", self.config.connection_id)

        scope = await self.load_scope()
        if scope:
            subscriptions = scope["subscriptions"]
            if subscriptions:
                for channel in subscriptions:
                    await self._backend.unsubscribe(
                        channel, connection_id=self.config.connection_id
                    )

        await self._backend.delete(self.config.connection_id)

    async def publish(self, channel: str, *, body: bytes) -> None:
        subscribers = await self._backend.get_subscribers(channel)
        tasks = []
        async with httpx.AsyncClient() as client:
            for connection_id in subscribers:
                if isinstance(connection_id, bytes):
                    connection_id = connection_id.decode()

                task = asyncio.create_task(
                    self.post_to_connection(
                        connection_id, client=client, body=body, channel=channel
                    )
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

    async def subscribe(self, channel: str, *, scope: Scope) -> None:
        await self._backend.subscribe(channel, connection_id=self.config.connection_id)
        scope["subscriptions"].append(channel)
        await self.save_scope(scope)

    async def unsubscribe(self, channel: str, *, scope: Scope) -> None:
        await self._backend.unsubscribe(
            channel, connection_id=self.config.connection_id
        )
        scope["subscriptions"].remove(channel)
        await self.save_scope(scope)

    async def send(self, body: bytes) -> None:
        await self.post_to_connection(self.config.connection_id, body=body)

    async def post_to_connection(
        self,
        connection_id: str,
        *,
        client: httpx.AsyncClient,
        body: bytes,
        channel: typing.Optional[str] = None,
    ) -> None:  # pragma: no cover

        loop = asyncio.get_event_loop()
        headers = await loop.run_in_executor(
            None, partial(get_sigv4_headers, body, self.config.api_gateway_region_name)
        )
        url = f"{self.config.api_gateway_endpoint_url}/@connections/{connection_id}"
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
