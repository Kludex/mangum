import os
import logging
from typing import AsyncIterator
from urllib.parse import urlparse, parse_qs
from contextlib import asynccontextmanager

import aioboto3
from botocore.exceptions import ClientError

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import WebSocketError

logger = logging.getLogger("mangum.backends.s3")


class S3Backend(WebSocketBackend):
    @asynccontextmanager
    async def connect(self) -> AsyncIterator:
        parsed_dsn = urlparse(self.dsn)
        parsed_query = parse_qs(parsed_dsn.query)
        self.bucket = parsed_dsn.hostname

        if parsed_dsn.path and parsed_dsn.path != "/":
            if not parsed_dsn.path.endswith("/"):
                self.key = parsed_dsn.path + "/"
            else:
                self.key = parsed_dsn.path
        else:
            self.key = ""

        region_name = parsed_query.get("region", os.environ["AWS_REGION"])
        async with aioboto3.client(
            "s3",
            region_name=region_name,
            # config=Config(connect_timeout=2, retries={"max_attempts": 0}),
            endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
        ) as self.client:
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
                await self.client.create_bucket(
                    Bucket=self.bucket,
                    # CreateBucketConfiguration={"LocationConstraint": region_name},
                )

            yield

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
