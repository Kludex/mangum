import os
import logging
from urllib.parse import urlparse, parse_qs


import aioboto3

# import boto3

# from botocore.client import Config
from botocore.exceptions import ClientError

from mangum.backends.base import WebSocketBackend


logger = logging.getLogger("mangum.websocket.s3")


class S3Backend(WebSocketBackend):
    async def connect(self) -> None:
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
        self.connection = await aioboto3.client(
            "s3",
            region_name=region_name,
            # config=Config(connect_timeout=2, retries={"max_attempts": 0}),
        ).__aenter__()  # Workaround limitation

        create_bucket = False

        try:
            await self.connection.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            error_code = int(exc.response["Error"]["Code"])
            if error_code == 403:  # pragma: no cover
                logger.error("S3 bucket access forbidden!")
            elif error_code == 404:
                logger.info(f"Bucket {self.bucket} not found, creating.")
                create_bucket = True

        if create_bucket:
            self.connection.create_bucket(
                Bucket=self.bucket,
                CreateBucketConfiguration={"LocationConstraint": region_name},
            )

    async def disconnect(self) -> None:
        await self.connection.__aexit__()

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.connection.put_object(
            Body=json_scope.encode(),
            Bucket=self.bucket,
            Key=f"{self.key}{connection_id}",
        )

    async def retrieve(self, connection_id: str) -> str:
        s3_object = await self.connection.get_object(
            Bucket=self.bucket, Key=f"{self.key}{connection_id}"
        )
        json_scope = s3_object["Body"].read().decode()

        return json_scope

    async def delete(self, connection_id: str) -> None:
        await self.connection.delete_object(
            Bucket=self.bucket, Key=f"{self.key}{connection_id}"
        )
