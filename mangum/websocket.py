import json
import logging
import typing
from dataclasses import dataclass, InitVar
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
    dsn: InitVar[str]
    api_gateway_region_name: str
    api_gateway_endpoint_url: str
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

    def on_connect(self, initial_scope: dict) -> None:
        self.logger.debug("Creating scope entry for %s", self.connection_id)
        initial_scope_json = json.dumps(initial_scope)
        self._backend.create(self.connection_id, initial_scope_json=initial_scope_json)

    def on_message(self, event: dict) -> Scope:
        self.logger.debug("Retrieving scope entry for %s", self.connection_id)
        scope_json = self._backend.retrieve(self.connection_id)
        scope = json.loads(scope_json)
        scope["aws.events"].append(event)
        self.update(scope)

        return scope

    def on_disconnect(self) -> None:
        self.logger.debug("Deleting scope entry for %s", self.connection_id)
        scope_json = self._backend.retrieve(self.connection_id)
        scope = json.loads(scope_json)
        subscriptions = scope["websocket.broadcast"]["subscriptions"]
        if subscriptions:
            for channel in subscriptions:
                self._backend.unsubscribe(self.connection_id, channel)

        self._backend.delete(self.connection_id)

    def update(self, scope: dict) -> None:
        scope_json = json.dumps(scope)
        self._backend.update(self.connection_id, updated_scope_json=scope_json)

    def publish(self, channel: str, *, body: bytes) -> None:
        subscribers = self._backend.get_subscribers(channel)
        for connection_id in subscribers:
            self.post_to_connection(connection_id.decode(), body=body, channel=channel)

    def subscribe(self, channel: str, *, scope: Scope) -> None:
        self._backend.subscribe(channel, connection_id=self.connection_id)
        scope["extensions"]["websocket.broadcast"]["subscriptions"].append(channel)
        self.update(scope)

    def unsubscribe(self, channel: str, *, scope: Scope) -> None:
        self._backend.unsubscribe(channel, connection_id=self.connection_id)
        scope["extensions"]["websocket.broadcast"]["subscriptions"].remove(channel)
        self.update(scope)

    def send(self, body: bytes) -> None:
        self.post_to_connection(self.connection_id, body=body)

    def post_to_connection(
        self, connection_id: str, *, body: bytes, channel: typing.Optional[str] = None
    ) -> None:  # pragma: no cover

        if self.api_gateway_client is None:
            self.api_gateway_client = boto3.client(
                "apigatewaymanagementapi",
                endpoint_url=self.api_gateway_endpoint_url,
                region_name=self.api_gateway_region_name,
            )

        try:
            self.api_gateway_client.post_to_connection(
                ConnectionId=connection_id, Data=body
            )
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 410:
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
            else:
                raise WebSocketError(exc)
