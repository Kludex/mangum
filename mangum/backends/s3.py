import typing
from dataclasses import dataclass

import boto3

from mangum.backends.base import WebSocketBackend


@dataclass
class S3Backend(WebSocketBackend):

    bucket_name: str
    region_name: typing.Optional[str] = None

    def __post_init__(self) -> None:
        # if region_name:
        #     region_name = self.region_name or os.environ.get("AWS_REGION", None)
        self.s3_client = boto3.client("s3")

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.s3_client.put_object(
            Body=initial_scope.encode(), Bucket=self.bucket_name, Key=connection_id
        )

    def fetch(self, connection_id: str) -> str:
        s3_object = self.s3_client.get_object(
            Bucket=self.bucket_name, Key=connection_id
        )
        initial_scope = s3_object["Body"].read().decode()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=connection_id)
