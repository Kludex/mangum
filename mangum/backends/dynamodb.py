import typing
import os
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import WebSocketError


@dataclass
class DynamoDBBackend(WebSocketBackend):

    table_name: str
    region_name: typing.Optional[str] = None
    dynamodb_endpoint_url: typing.Optional[str] = None

    def __post_init__(self) -> None:
        region_name = self.region_name or os.environ.get("AWS_REGION", None)
        if not region_name:
            raise WebSocketError("Could not determine region for DynamoDB resource.")

        try:
            dynamodb_resource = boto3.resource(
                "dynamodb",
                region_name=region_name,
                endpoint_url=self.dynamodb_endpoint_url,
            )
            dynamodb_resource.meta.client.describe_table(TableName=self.table_name)
        except KeyError as exc:
            raise WebSocketError(f"You must set {exc} in the environment variables.")
        except ClientError as exc:
            raise WebSocketError(exc)
        self.database = dynamodb_resource.Table(self.table_name)

    def create(self, connection_id: str, initial_scope: str) -> None:
        try:
            self.database.put_item(
                Item={"connectionId": connection_id, "initial_scope": initial_scope},
                ConditionExpression=f"attribute_not_exists(connectionId)",
            )
        except ClientError as exc:
            raise WebSocketError(exc)

    def fetch(self, connection_id: str) -> str:
        try:
            initial_scope = (
                self.database.get_item(Key={"connectionId": connection_id})
                .get("Item", {})
                .get("initial_scope", None)
            )
        except ClientError as exc:
            raise WebSocketError(exc)

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.database.delete_item(Key={"connectionId": connection_id})
