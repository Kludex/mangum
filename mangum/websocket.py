import json
import logging
import typing
from dataclasses import dataclass
from urllib.parse import urlparse

from mangum.types import Scope
from mangum.exceptions import WebSocketError, ConfigurationError

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover
    boto3 = None


@dataclass
class WebSocket:

    connection_id: str
    dsn: str
    api_gateway_region_name: str
    api_gateway_endpoint_url: str

    def __post_init__(self) -> None:
        if boto3 is None:  # pragma: no cover
            raise WebSocketError("boto3 must be installed to use WebSockets.")
        self.logger: logging.Logger = logging.getLogger("mangum.websocket")
        parsed_dsn = urlparse(self.dsn)
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

            self._backend = SQLiteBackend(self.dsn)  # type: ignore
        elif scheme == "dynamodb":
            from mangum.backends.dynamodb import DynamoDBBackend

            self._backend = DynamoDBBackend(self.dsn)  # type: ignore
        elif scheme == "s3":
            from mangum.backends.s3 import S3Backend

            self._backend = S3Backend(self.dsn)  # type: ignore

        elif scheme in ("postgresql", "postgres"):
            from mangum.backends.postgresql import PostgreSQLBackend

            self._backend = PostgreSQLBackend(self.dsn)  # type: ignore

        elif scheme == "redis":
            from mangum.backends.redis import RedisBackend

            self._backend = RedisBackend(self.dsn)  # type: ignore

        else:
            raise ConfigurationError(f"{scheme} does not match a supported backend.")
        self.logger.debug("WebSocket backend connection established.")

    def create(self, initial_scope: dict) -> None:
        self.logger.debug("Creating scope entry for %s", self.connection_id)
        initial_scope_json = json.dumps(initial_scope)
        self._backend.create(self.connection_id, initial_scope_json)

    def fetch(self) -> None:
        self.logger.debug("Fetching scope entry for %s", self.connection_id)
        initial_scope = self._backend.fetch(self.connection_id)
        scope = json.loads(initial_scope)
        query_string = scope["query_string"]
        headers = scope["headers"]
        if headers:
            headers = [[k.encode(), v.encode()] for k, v in headers.items() if headers]
        scope.update({"headers": headers, "query_string": query_string.encode()})
        self.scope: Scope = scope

    def delete(self, connection_id: str) -> None:
        self.logger.debug("Deleting scope entry for %s", connection_id)
        self._backend.delete(connection_id)

    def send(self, body: bytes) -> None:
        self.post_to_connection(self.connection_id, body=body)

    def publish(self, channel: str, *, body: bytes) -> None:
        subscribers = self._backend.get_subscribers(channel)
        for connection_id in subscribers:
            self.post_to_connection(connection_id.decode(), body=body, channel=channel)

    def subscribe(self, channel: str) -> None:
        self._backend.add_subscriber(self.connection_id, channel=channel)

    def unsubscribe(self, connection_id: str, channel: str) -> None:
        self._backend.remove_subscriber(connection_id, channel=channel)

    def post_to_connection(
        self, connection_id: str, *, body: bytes, channel: typing.Optional[str] = None
    ) -> None:  # pragma: no cover
        try:
            apigw_client = boto3.client(
                "apigatewaymanagementapi",
                endpoint_url=self.api_gateway_endpoint_url,
                region_name=self.api_gateway_region_name,
            )

            apigw_client.post_to_connection(ConnectionId=connection_id, Data=body)
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 410:
                if channel:
                    self.unsubscribe(connection_id, channel=channel)
                self.delete(connection_id)
            else:
                raise WebSocketError(exc)
