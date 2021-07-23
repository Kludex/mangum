import asyncio
import logging
from typing import Dict, Optional
import json
from functools import partial
from dataclasses import dataclass, InitVar
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

try:
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore


from .base import WebSocketBackend
from ..exceptions import WebSocketError, ConfigurationError
from ..types import Scope


def get_sigv4_headers(
    method: str,
    url: str,
    data: Optional[bytes] = None,
    region_name: Optional[str] = None,
) -> Dict:
    session = boto3.Session()
    credentials = session.get_credentials()
    creds = credentials.get_frozen_credentials()
    region = region_name or session.region_name

    request = AWSRequest(method=method, url=url, data=data)
    SigV4Auth(creds, "execute-api", region).add_auth(request)

    return dict(request.headers)


@dataclass
class WebSocket:
    """
    A `WebSocket` connection handler interface for the
    selected `WebSocketBackend` subclass
    """

    dsn: InitVar[Optional[str]]
    api_gateway_endpoint_url: str
    api_gateway_region_name: Optional[str] = None

    def __post_init__(self, dsn: Optional[str]) -> None:
        if boto3 is None:  # pragma: no cover
            raise WebSocketError("boto3 must be installed to use WebSockets.")

        if httpx is None:  # pragma: no cover
            raise WebSocketError("httpx must be installed to use WebSockets.")

        if dsn is None:
            raise ConfigurationError(
                "The `dsn` parameter must be provided for WebSocket connections."
            )

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

            self._Backend = SQLiteBackend  # type: ignore

        elif scheme == "dynamodb":
            from mangum.backends.dynamodb import DynamoDBBackend

            self._Backend = DynamoDBBackend  # type: ignore

        elif scheme == "s3":
            from mangum.backends.s3 import S3Backend

            self._Backend = S3Backend  # type: ignore

        elif scheme in ("postgresql", "postgres"):
            from mangum.backends.postgresql import PostgreSQLBackend

            self._Backend = PostgreSQLBackend  # type: ignore

        elif scheme == "redis":
            from mangum.backends.redis import RedisBackend

            self._Backend = RedisBackend  # type: ignore

        else:
            raise ConfigurationError(f"{scheme} does not match a supported backend.")

        self.dsn = dsn

        self.logger.info("WebSocket backend connection established.")

    async def load_scope(self, backend: WebSocketBackend, connection_id: str) -> Scope:
        loaded_scope = await backend.retrieve(connection_id)
        scope = json.loads(loaded_scope)
        scope.update(
            {
                "query_string": scope["query_string"].encode(),
                "headers": [[h[0].encode(), h[1].encode()] for h in scope["headers"]],
                "client": tuple(scope["client"]),
                "server": tuple(scope["server"]),
            }
        )

        return scope

    async def save_scope(
        self, backend: WebSocketBackend, connection_id: str, scope: Scope
    ) -> None:
        scope.update(
            {
                "query_string": scope["query_string"].decode(),
                "headers": [[h[0].decode(), h[1].decode()] for h in scope["headers"]],
            }
        )
        json_scope = json.dumps(scope)
        await backend.save(connection_id, json_scope=json_scope)

    async def on_connect(self, connection_id: str, initial_scope: Scope) -> None:
        self.logger.debug("Creating scope entry for %s", connection_id)
        async with self._Backend(self.dsn) as backend:  # type: ignore
            await self.save_scope(backend, connection_id, initial_scope)

    async def on_message(self, connection_id: str) -> Scope:
        self.logger.debug("Retrieving scope entry for %s", connection_id)
        async with self._Backend(self.dsn) as backend:  # type: ignore
            scope = await self.load_scope(backend, connection_id)
        return scope

    async def on_disconnect(self, connection_id: str) -> None:
        self.logger.debug("Deleting scope entry for %s", connection_id)
        async with self._Backend(self.dsn) as backend:  # type: ignore
            await backend.delete(connection_id)

    async def post_to_connection(self, connection_id: str, body: bytes) -> None:
        async with httpx.AsyncClient() as client:
            await self._post_to_connection(connection_id, client=client, body=body)

    async def delete_connection(self, connection_id: str) -> None:
        async with httpx.AsyncClient() as client:
            await self._request_to_connection("DELETE", connection_id, client=client)

    async def _post_to_connection(
        self,
        connection_id: str,
        *,
        client: "httpx.AsyncClient",
        body: bytes,
    ) -> None:  # pragma: no cover
        response = await self._request_to_connection(
            "POST", connection_id, client=client, body=body
        )

        if response.status_code == 410:
            await self.on_disconnect(connection_id)
        elif response.status_code != 200:
            raise WebSocketError(f"Error: {response.status_code}")

    async def _request_to_connection(
        self,
        method: str,
        connection_id: str,
        *,
        client: "httpx.AsyncClient",
        body: Optional[bytes] = None,
    ) -> "httpx.Response":
        loop = asyncio.get_event_loop()
        url = f"{self.api_gateway_endpoint_url}/{connection_id}"
        headers = await loop.run_in_executor(
            None,
            partial(
                get_sigv4_headers,
                method,
                url,
                body,
                self.api_gateway_region_name,
            ),
        )

        return await client.request(method, url, content=body, headers=headers)
