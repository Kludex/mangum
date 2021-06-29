import os
import logging
from typing import Any
from urllib.parse import ParseResult, urlparse, parse_qs

import aioboto3
from botocore.exceptions import ClientError

from .base import WebSocketBackend
from ..exceptions import WebSocketError

logger = logging.getLogger("mangum.backends.s3")


def get_file_key(parsed_dsn: ParseResult) -> str:
    if parsed_dsn.path and parsed_dsn.path != "/":
        if not parsed_dsn.path.endswith("/"):
            return parsed_dsn.path + "/"
        return parsed_dsn.path

    return ""


class S3Backend(WebSocketBackend):
    async def __aenter__(self) -> WebSocketBackend:
        parsed_dsn = urlparse(self.dsn)
        parsed_query = parse_qs(parsed_dsn.query)
        self.bucket = parsed_dsn.hostname
        self.key = get_file_key(parsed_dsn)
        self.region_name = (
            parsed_query["region"][0]
            if "region" in parsed_query
            else os.environ["AWS_REGION"]
        )
        self.endpoint_url = (
            parsed_query["endpoint_url"][0] if "endpoint_url" in parsed_query else None
        )

        session = aioboto3.Session()
        self.client = await session.client(
            "s3",
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
        ).__aenter__()

        create_bucket = False

        try:
            await self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            error_code = int(exc.response["Error"]["Code"])
            if error_code == 403:  # pragma: no cover
                logger.error("S3 bucket access forbidden!")
            elif error_code == 404:
                logger.info(f"Bucket {self.bucket} not found, creating.")
                create_bucket = True

        if create_bucket:
            await self.client.create_bucket(Bucket=self.bucket)

        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.client.__aexit__(*exc_info)

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.client.put_object(
            Body=json_scope.encode(),
            Bucket=self.bucket,
            Key=f"{self.key}{connection_id}",
        )

    async def retrieve(self, connection_id: str) -> str:
        try:
            s3_object = await self.client.get_object(
                Bucket=self.bucket, Key=f"{self.key}{connection_id}"
            )
        except self.client.exceptions.NoSuchKey:
            raise WebSocketError(f"Connection not found: {connection_id}")

        async with s3_object["Body"] as body:
            scope = await body.read()
            json_scope = scope.decode()

        return json_scope

    async def delete(self, connection_id: str) -> None:
        await self.client.delete_object(
            Bucket=self.bucket, Key=f"{self.key}{connection_id}"
        )
