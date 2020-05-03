import os
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import WebSocketError, ConfigurationError


@dataclass
class DynamoDBBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        try:
            table_name = self.params["table_name"]
        except KeyError:
            raise ConfigurationError("DynamoDB 'table_name' missing.")
        region_name = self.params.get("region_name", os.environ["AWS_REGION"])
        endpoint_url = self.params.get("endpoint_url", None)
        try:
            dynamodb_resource = boto3.resource(
                "dynamodb", region_name=region_name, endpoint_url=endpoint_url
            )
            dynamodb_resource.meta.client.describe_table(TableName=table_name)
        except ClientError as exc:
            raise WebSocketError(exc)

        self.connection = dynamodb_resource.Table(table_name)

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.connection.put_item(
            Item={"connectionId": connection_id, "initial_scope": initial_scope},
            ConditionExpression=f"attribute_not_exists(connectionId)",
        )

    def fetch(self, connection_id: str) -> str:
        try:
            item = self.connection.get_item(Key={"connectionId": connection_id})["Item"]
        except KeyError:
            raise WebSocketError(f"Connection not found: {connection_id}")

        initial_scope = item["initial_scope"]

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.connection.delete_item(Key={"connectionId": connection_id})
