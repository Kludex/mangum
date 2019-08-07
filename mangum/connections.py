import typing
import os

import boto3
import botocore
from boto3.dynamodb.conditions import Attr

from mangum.exceptions import ConnectionTableException


class ConnectionTable:
    """
    Represents a DynamoDB resource that contains the WebSocket connection table.
    """

    def __init__(self) -> None:
        dynamodb = boto3.resource("dynamodb", region_name=os.environ["REGION_NAME"])
        self.table = dynamodb.Table(os.environ["TABLE_NAME"])

    def get_item(self, connection_id: str) -> typing.Union[typing.Dict, None]:
        """
        Retrieve an item in the connection table by id.
        """
        item = self.table.get_item(Key={"connectionId": connection_id}).get(
            "Item", None
        )
        return item

    def update_item(self, connection_id: str, **kwargs) -> int:
        """
        Update an item in the connection table by id.
        """
        result = self.table.put_item(Item={**{"connectionId": connection_id}, **kwargs})
        return result.get("ResponseMetadata", {}).get("HTTPStatusCode")

    def delete_item(self, connection_id: str) -> int:
        """
        Delete an item in the connection table by id.
        """
        result = self.table.delete_item(Key={"connectionId": connection_id})
        return result.get("ResponseMetadata", {}).get("HTTPStatusCode")

    def get_group_items(
        self, group: str
    ) -> typing.Union[typing.List[typing.Dict], None]:
        """
        Retrieve a list of items in the connection table by group.
        """
        items = self.table.scan(
            ProjectionExpression="connectionId",
            FilterExpression=Attr("groups").contains(group),
        ).get("Items", None)
        return items

    def send_data(
        self, items: typing.List[typing.Dict], data: str
    ) -> None:  # pragma: no cover
        """
        Send data to one or more items in the connection table.
        """
        apigw_management = boto3.client(
            "apigatewaymanagementapi", endpoint_url=self.endpoint_url
        )
        for item in items:
            try:
                apigw_management.post_to_connection(
                    ConnectionId=item["connectionId"], Data=data
                )
            except botocore.exceptions.ClientError as exc:
                status_code = exc.response.get("ResponseMetadata", {}).get(
                    "HTTPStatusCode"
                )
                if status_code == 410:
                    # Delete stale connection
                    self.connection_table.delete_item(
                        Key={"connectionId": item["connectionId"]}
                    )
                else:
                    raise ConnectionTableException("Connection does not exist")
