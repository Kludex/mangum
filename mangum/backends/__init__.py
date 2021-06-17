import asyncio
import logging
import typing
import json
import os
import hashlib
import hmac
import datetime
from functools import partial
from dataclasses import dataclass, InitVar
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover <--
    httpx = None  # type: ignore

from mangum.exceptions import WebSocketError, ConfigurationError
from mangum.types import Scope


def sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def get_sigv4_headers(body: bytes, region_name: str) -> dict:
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
    """
    A `WebSocket` connection handler interface for the
    selected `WebSocketBackend` subclass
    """

    dsn: InitVar[str]
    connection_id: str
    api_gateway_endpoint_url: str
    api_gateway_region_name: typing.Optional[str] = None

    def __post_init__(self, dsn: str) -> None:
        if httpx is None:  # pragma: no cover
            raise WebSocketError("httpx must be installed to use WebSockets.")

        self.logger: logging.Logger = logging.getLogger("mangum.backends")
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
        self.logger.info("WebSocket backend connection established.")

    async def load_scope(self) -> Scope:
        loaded_scope = await self._backend.retrieve(self.connection_id)
        scope = json.loads(loaded_scope)
        scope.update(
            {
                "query_string": scope["query_string"].encode(),
                "headers": [
                    [k.encode(), v.encode()] for k, v in scope["headers"].items()
                ],
            }
        )

        return scope

    async def save_scope(self, scope: Scope) -> None:
        scope.update(
            {
                "query_string": scope["query_string"].decode(),
                "headers": {h[0].decode(): h[1].decode() for h in scope["headers"]},
            }
        )
        json_scope = json.dumps(scope)
        await self._backend.save(self.connection_id, json_scope=json_scope)

    async def on_connect(self, initial_scope: Scope) -> None:
        await self._backend.connect()
        self.logger.debug("Creating scope entry for %s", self.connection_id)
        await self.save_scope(initial_scope)
        await self._backend.disconnect()

    async def on_message(self) -> Scope:
        await self._backend.connect()
        self.logger.debug("Retrieving scope entry for %s", self.connection_id)
        scope = await self.load_scope()
        await self._backend.disconnect()
        return scope

    async def on_disconnect(self) -> None:
        await self._backend.connect()
        self.logger.debug("Deleting scope entry for %s", self.connection_id)
        await self._backend.delete(self.connection_id)
        await self._backend.disconnect()

    async def post_to_connection(self, body: bytes) -> None:
        async with httpx.AsyncClient() as client:
            await self._post_to_connection(client=client, body=body)

    async def delete_connection(self) -> None:
        async with httpx.AsyncClient() as client:
            await client.delete(self.api_gateway_endpoint_url)

    async def _post_to_connection(
        self,
        *,
        client: "httpx.AsyncClient",
        body: bytes,
    ) -> None:  # pragma: no cover
        loop = asyncio.get_event_loop()
        headers = await loop.run_in_executor(
            None, partial(get_sigv4_headers, body, self.api_gateway_region_name)
        )

        response = await client.post(
            self.api_gateway_endpoint_url, content=body, headers=headers
        )
        if response.status_code == 410:
            await self.on_disconnect()
        elif response.status_code != 200:
            raise WebSocketError(f"Error: {response.status_code}")
