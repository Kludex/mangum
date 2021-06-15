import os
from urllib.parse import ParseResult, urlparse, parse_qs
import logging

import aioboto3

# from botocore.config import Config
from botocore.exceptions import ClientError

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import WebSocketError

logger = logging.getLogger("mangum.backends.dynamodb")


def get_table_name(parsed_dsn: ParseResult) -> str:
    netloc = parsed_dsn.netloc
    _, _, hostinfo = netloc.rpartition("@")
    hostname, _, _ = hostinfo.partition(":")
    return hostname


class DynamoDBBackend(WebSocketBackend):
    async def connect(self) -> None:
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

        create_table = False

        try:
            self.dynamodb_resource = await aioboto3.resource(
                "dynamodb",
                region_name=region_name,
                endpoint_url=endpoint_url,
                # config=Config(connect_timeout=2, retries={"max_attempts": 0}),
            ).__aenter__()
            await self.dynamodb_resource.meta.client.describe_table(
                TableName=table_name
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(f"Table {table_name} not found, creating.")
                create_table = True
            else:
                raise WebSocketError(exc)

        if create_table:
            client = self.dynamodb_resource.meta.client
            await client.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "connectionId", "AttributeType": "S"}
                ],
                ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            )
            self.connection = await self.dynamodb_resource.Table(table_name)
            await self.connection.wait_until_exists()
        else:
            self.connection = await self.dynamodb_resource.Table(table_name)

    async def disconnect(self) -> None:
        await self.dynamodb_resource.__aexit__(None, None, None)

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.connection.put_item(
            Item={"connectionId": connection_id, "initial_scope": json_scope},
            ConditionExpression=f"attribute_not_exists(connectionId)",
        )

    async def retrieve(self, connection_id: str) -> str:
        try:
            response = await self.connection.get_item(
                Key={"connectionId": connection_id}
            )
            item = response["Item"]
        except KeyError:
            raise WebSocketError(f"Connection not found: {connection_id}")
        initial_scope = item["initial_scope"]
        return initial_scope

    async def delete(self, connection_id: str) -> None:
        await self.connection.delete_item(Key={"connectionId": connection_id})
