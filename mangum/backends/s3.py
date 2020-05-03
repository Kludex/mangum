import os
import logging
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import ConfigurationError


@dataclass
class S3Backend(WebSocketBackend):
    def __post_init__(self) -> None:
        self.logger = logging.getLogger("mangum.websocket.s3")
        try:
            self.bucket = self.params["bucket"]
        except KeyError:
            raise ConfigurationError("S3 'bucket' parameter missing.")
        region_name = self.params.get("region_name", os.environ["AWS_REGION"])
        self.connection = boto3.client("s3", region_name=region_name)
        create_bucket = False

        try:
            self.connection.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            error_code = int(exc.response["Error"]["Code"])
            if error_code == 403:
                self.logger.error("S3 bucket access forbidden!")
            elif error_code == 404:
                self.logger.info(f"Bucket {self.bucket} not found, creating.")
                create_bucket = True

        if create_bucket:
            self.connection.create_bucket(
                Bucket=self.bucket,
                CreateBucketConfiguration={"LocationConstraint": region_name},
            )

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.connection.put_object(
            Body=initial_scope.encode(), Bucket=self.bucket, Key=connection_id
        )

    def fetch(self, connection_id: str) -> str:
        s3_object = self.connection.get_object(Bucket=self.bucket, Key=connection_id)
        initial_scope = s3_object["Body"].read().decode()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.connection.delete_object(Bucket=self.bucket, Key=connection_id)
