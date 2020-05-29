# import os
# import logging
# from dataclasses import dataclass
# from urllib.parse import urlparse, parse_qs


# import boto3
# from botocore.client import Config
# from botocore.exceptions import ClientError

# from mangum.backends.base import WebSocketBackend


# logger = logging.getLogger("mangum.websocket.s3")


# @dataclass
# class S3Backend(WebSocketBackend):
#     def __post_init__(self) -> None:
#         parsed_dsn = urlparse(self.dsn)
#         parsed_query = parse_qs(parsed_dsn.query)
#         self.bucket = parsed_dsn.hostname
#         if parsed_dsn.path and parsed_dsn.path != "/":
#             if not parsed_dsn.path.endswith("/"):
#                 self.key = parsed_dsn.path + "/"
#             else:
#                 self.key = parsed_dsn.path
#         else:
#             self.key = ""
#         region_name = parsed_query.get("region", os.environ["AWS_REGION"])
#         create_bucket = False
#         self.connection = boto3.client(
#             "s3",
#             region_name=region_name,
#             config=Config(connect_timeout=2, retries={"max_attempts": 0}),
#         )
#         try:
#             self.connection.head_bucket(Bucket=self.bucket)
#         except ClientError as exc:
#             error_code = int(exc.response["Error"]["Code"])
#             if error_code == 403:  # pragma: no cover
#                 logger.error("S3 bucket access forbidden!")
#             elif error_code == 404:
#                 logger.info(f"Bucket {self.bucket} not found, creating.")
#                 create_bucket = True
#         if create_bucket:
#             self.connection.create_bucket(
#                 Bucket=self.bucket,
#                 CreateBucketConfiguration={"LocationConstraint": region_name},
#             )

#     def save(self, connection_id: str, *, json_scope: str) -> None:
#         self.connection.put_object(
#             Body=json_scope.encode(),
#             Bucket=self.bucket,
#             Key=f"{self.key}{connection_id}",
#         )

#     def retrieve(self, connection_id: str) -> str:
#         s3_object = self.connection.get_object(
#             Bucket=self.bucket, Key=f"{self.key}{connection_id}"
#         )
#         json_scope = s3_object["Body"].read().decode()

#         return json_scope

#     def delete(self, connection_id: str) -> None:
#         self.connection.delete_object(
#             Bucket=self.bucket, Key=f"{self.key}{connection_id}"
#         )

#     def subscribe(self, channel: str, *, connection_id: str) -> None:
#         self.connection.put_object(
#             Bucket=self.bucket, Key=f"{self.key}channels/{channel}/{connection_id}"
#         )

#     def unsubscribe(self, channel: str, *, connection_id: str) -> None:
#         self.connection.delete_object(
#             Bucket=self.bucket, Key=f"{self.key}channels/{channel}/{connection_id}"
#         )

#     def get_subscribers(self, channel: str) -> list:
#         subscribers = []
#         prefix = f"{self.key}channels/{channel}/"
#         paginator = self.connection.get_paginator("list_objects")
#         paginated = paginator.paginate(Bucket=self.bucket)
#         for page in paginated:
#             for obj in page["Contents"]:
#                 if obj["Key"].startswith(prefix):
#                     connection_id = obj["Key"].replace(prefix, "")
#                     subscribers.append(connection_id)

#         return subscribers
