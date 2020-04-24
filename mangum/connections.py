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

    client_id: str
    client_id_field: str = os.environ.get("WS_CLIENT_ID_FIELD", "client_id")
    region_name: str = os.environ.get("WS_REGION_NAME", "ap-southeast-1")
    table_name: str = os.environ.get("WS_TABLE_NAME", "mangum")
    endpoint_url: typing.Optional[str] = None

    def __post_init__(self) -> None:
        try:
            dynamodb_resource = boto3.resource("dynamodb", region_name=self.region_name)
            dynamodb_resource.meta.client.describe_table(TableName=self.table_name)
        except ClientError as exc:
            raise WebSocketError(exc)
        self.dynamodb_table = dynamodb_resource.Table(self.table_name)

    @property
    def client_key(self) -> dict:
        return {self.client_id_field: self.client_id}

    def accept(self, initial_scope: Scope) -> None:
        client = {"initial_scope": json.dumps(initial_scope)}
        client.update(self.client_key)
        try:
            self.dynamodb_table.put_item(
                Item=client,
                ConditionExpression=f"attribute_not_exists({self.client_id_field})",
            )
        except ClientError as exc:
            raise WebSocketError(exc)

    def connect(self) -> None:
        try:
            client = self.dynamodb_table.get_item(Key=self.client_key)["Item"]
        except (ClientError, KeyError) as exc:
            raise WebSocketError(exc)

        scope = json.loads(client["initial_scope"])
        query_string = scope["query_string"]
        headers = scope["headers"]
        if headers:
            headers = [[k.encode(), v.encode()] for k, v in headers.items() if headers]
        scope.update({"headers": headers, "query_string": query_string.encode()})
        self.scope = scope

    def send(self, text_data: str) -> None:  # pragma: no cover
        try:
            apigw_client = boto3.client(
                "apigatewaymanagementapi", endpoint_url=self.endpoint_url
            )
            apigw_client.post_to_connection(ConnectionId=self.client_id, Data=text_data)
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 410:
                self.disconnect()
            else:
                raise WebSocketError(exc)

    def disconnect(self) -> None:
        try:
            self.dynamodb_table.delete_item(Key=self.client_key)
        except ClientError as exc:  # pragma: no cover
            raise WebSocketError(exc)
