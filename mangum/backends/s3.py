import os
from dataclasses import dataclass

import boto3

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import ConfigurationError


@dataclass
class S3Backend(WebSocketBackend):
    def __post_init__(self) -> None:
        try:
            self.bucket = self.params["bucket"]
        except KeyError:
            raise ConfigurationError("S3 'bucket' name missing.")
        region_name = self.params.get("region_name", os.environ["AWS_REGION"])
        self.connection = boto3.client("s3", region_name=region_name)

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
