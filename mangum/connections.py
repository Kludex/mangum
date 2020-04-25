import typing
import os
import json
from dataclasses import dataclass

from mangum.exceptions import WebSocketError
from mangum.types import Scope

try:
    import boto3
    from botocore.exceptions import ClientError

    __ERR__ = ""
except ImportError:  # pragma: no cover
    __ERR__ = "boto3 must be installed for WebSocket support."


@dataclass
class WebSocket:

    connection_id: str
    endpoint_url: typing.Optional[str] = None

    def __post_init__(self) -> None:
        try:
            region_name = os.environ["TABLE_REGION"]
            table_name = os.environ["TABLE_NAME"]
            dynamodb_resource = boto3.resource(
                "dynamodb",
                region_name=region_name,
                endpoint_url=os.environ.get("TABLE_ENDPOINT_URL", None),
            )
            dynamodb_resource.meta.client.describe_table(TableName=table_name)
        except KeyError as exc:
            raise WebSocketError(f"You must set {exc} in the environment variables.")
        except ClientError as exc:
            raise WebSocketError(exc)
        self.dynamodb_table = dynamodb_resource.Table(table_name)

    @property
    def connection_key(self) -> dict:
        return {"connectionId": self.connection_id}

    def accept(self, initial_scope: Scope) -> None:
        connection = {"initial_scope": json.dumps(initial_scope)}
        connection.update(self.connection_key)
        try:
            self.dynamodb_table.put_item(
                Item=connection,
                ConditionExpression=f"attribute_not_exists(connectionId)",
            )
        except ClientError as exc:
            raise WebSocketError(exc)

    def connect(self) -> None:
        try:
            connection = self.dynamodb_table.get_item(
                Key={"connectionId": self.connection_id}
            )["Item"]
        except ClientError as exc:  # pragma: no cover
            raise WebSocketError(exc)
        except KeyError:
            raise WebSocketError(f"Connection not found: {self.connection_key}")

        scope = json.loads(connection["initial_scope"])
        query_string = scope["query_string"]
        headers = scope["headers"]
        if headers:
            headers = [[k.encode(), v.encode()] for k, v in headers.items() if headers]
        scope.update({"headers": headers, "query_string": query_string.encode()})
        self.scope = scope

    def send(self, msg_data: bytes) -> None:  # pragma: no cover
        try:
            apigw_client = boto3.client(
                "apigatewaymanagementapi", endpoint_url=self.endpoint_url
            )
            apigw_client.post_to_connection(
                ConnectionId=self.connection_id, Data=msg_data
            )
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 410:
                self.disconnect()
            else:
                raise WebSocketError(exc)

    def disconnect(self) -> None:
        try:
            self.dynamodb_table.delete_item(Key=self.connection_key)
        except ClientError as exc:  # pragma: no cover
            raise WebSocketError(exc)
