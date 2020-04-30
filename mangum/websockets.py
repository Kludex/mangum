import typing
import json
import logging
from dataclasses import dataclass

from mangum.types import Scope
from mangum.exceptions import WebSocketError


import boto3
from botocore.exceptions import ClientError


@dataclass
class WebSocket:

    connection_id: str
    api_gateway_endpoint_url: str
    ws_config: typing.Optional[dict]

    def __post_init__(self) -> None:
        if self.ws_config is None:
            raise WebSocketError(
                "A `ws_config` argument is required to configure WebSocket support."
            )
        self.logger: logging.Logger = logging.getLogger("mangum.websocket")
        config = self.ws_config.copy()
        backend = config.pop("backend")
        if backend == "sqlite3":
            self.logger.info(
                "The `SQLiteBackend` (without s3) should be only be used for local "
                "debugging. It will not work in a deployed environment."
            )
            from mangum.backends.sqlite3 import SQLite3Backend

            self._backend = SQLite3Backend(**config)  # type: ignore
        elif backend == "dynamodb":
            from mangum.backends.dynamodb import DynamoDBBackend

            self._backend = DynamoDBBackend(**config)  # type: ignore
        elif backend == "s3":
            from mangum.backends.s3 import S3Backend

            self._backend = S3Backend(**config)  # type: ignore

        elif backend == "postgres":
            from mangum.backends.postgres import PostgreSQLBackend

            self._backend = PostgreSQLBackend(**config)  # type: ignore
        else:
            raise WebSocketError(f"Invalid backend specified: {backend}")

    def create(self, initial_scope: dict) -> None:
        initial_scope_json = json.dumps(initial_scope)
        self._backend.create(self.connection_id, initial_scope_json)

    def fetch(self) -> None:
        initial_scope = self._backend.fetch(self.connection_id)
        scope = json.loads(initial_scope)
        query_string = scope["query_string"]
        headers = scope["headers"]
        if headers:
            headers = [[k.encode(), v.encode()] for k, v in headers.items() if headers]
        scope.update({"headers": headers, "query_string": query_string.encode()})
        self.scope: Scope = scope

    def delete(self) -> None:
        self._backend.delete(self.connection_id)

    def post_to_connection(self, msg_data: bytes) -> None:  # pragma: no cover
        try:
            apigw_client = boto3.client(
                "apigatewaymanagementapi", endpoint_url=self.api_gateway_endpoint_url
            )
            apigw_client.post_to_connection(
                ConnectionId=self.connection_id, Data=msg_data
            )
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 410:
                self.delete()
            else:
                raise WebSocketError(exc)
