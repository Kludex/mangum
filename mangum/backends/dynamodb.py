import os
from typing import Any
from urllib.parse import ParseResult, urlparse, parse_qs
import logging

import aioboto3
from botocore.exceptions import ClientError

from .base import WebSocketBackend
from ..exceptions import WebSocketError

logger = logging.getLogger("mangum.backends.dynamodb")


def get_table_name(parsed_dsn: ParseResult) -> str:
    netloc = parsed_dsn.netloc
    _, _, hostinfo = netloc.rpartition("@")
    hostname, _, _ = hostinfo.partition(":")
    return hostname


class DynamoDBBackend(WebSocketBackend):
    async def __aenter__(self) -> WebSocketBackend:
        parsed_dsn = urlparse(self.dsn)
        parsed_query = parse_qs(parsed_dsn.query)
        self.table_name = get_table_name(parsed_dsn)
        self.region_name = (
            parsed_query["region"][0]
            if "region" in parsed_query
            else os.environ["AWS_REGION"]
        )
        self.endpoint_url = (
            parsed_query["endpoint_url"][0] if "endpoint_url" in parsed_query else None
        )

        session = aioboto3.Session()
        self.resource = await session.resource(
            "dynamodb",
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
        ).__aenter__()

        create_table = False

        try:
            await self.resource.meta.client.describe_table(TableName=self.table_name)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(f"Table {self.table_name} not found, creating.")
                create_table = True
            else:  # pragma: no cover
                await self.__aexit__(None, None, None)
                raise WebSocketError(exc)

        self.table = await self.resource.Table(self.table_name)

        if create_table:
            client = self.resource.meta.client
            await client.create_table(
                TableName=self.table_name,
                KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "connectionId", "AttributeType": "S"}
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            )
            await self.table.wait_until_exists()

        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.resource.__aexit__(*exc_info)

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.table.put_item(
            Item={"connectionId": connection_id, "initial_scope": json_scope},
            ConditionExpression="attribute_not_exists(connectionId)",
        )

    async def retrieve(self, connection_id: str) -> str:
        try:
            response = await self.table.get_item(Key={"connectionId": connection_id})
            item = response["Item"]
        except KeyError:
            raise WebSocketError(f"Connection not found: {connection_id}")
        initial_scope = item["initial_scope"]
        return initial_scope

    async def delete(self, connection_id: str) -> None:
        await self.table.delete_item(Key={"connectionId": connection_id})
