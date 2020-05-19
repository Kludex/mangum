import os

from urllib.parse import ParseResult, urlparse, parse_qs
from dataclasses import dataclass

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import WebSocketError


def get_table_name(parsed_dsn: ParseResult) -> str:
    netloc = parsed_dsn.netloc
    _, _, hostinfo = netloc.rpartition("@")
    hostname, _, _ = hostinfo.partition(":")
    return hostname


@dataclass
class DynamoDBBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        parsed_dsn = urlparse(self.dsn)
        parsed_query = parse_qs(parsed_dsn.query)
        table_name = get_table_name(parsed_dsn)

        region_name = (
            parsed_query["region"][0]
            if "region" in parsed_query
            else os.environ["AWS_REGION"]
        )
        endpoint_url = (
            parsed_query["endpoint_url"][0] if "endpoint_url" in parsed_query else None
        )
        try:
            dynamodb_resource = boto3.resource(
                "dynamodb",
                region_name=region_name,
                endpoint_url=endpoint_url,
                config=Config(connect_timeout=2, retries={"max_attempts": 0}),
            )
            dynamodb_resource.meta.client.describe_table(TableName=table_name)
        except (EndpointConnectionError, ClientError) as exc:
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
