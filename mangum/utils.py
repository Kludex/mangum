import logging
import os

import boto3
import botocore


def get_connections():
    db = boto3.resource("dynamodb")
    connections = db.Table(os.environ["TABLE_NAME"])
    return connections


def send_to_connections(*, data, connections, items, endpoint_url):
    apigw_management = boto3.client(
        "apigatewaymanagementapi", endpoint_url=endpoint_url
    )
    for item in items:
        try:
            apigw_management.post_to_connection(
                ConnectionId=item["connectionId"], Data=data
            )
        except botocore.exceptions.ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 410:
                connections.delete_item(Key={"connectionId": item["connectionId"]})
            else:
                return make_response("Connection error", status_code=500)
    return make_response("OK", status_code=200)


def make_response(content: str, status_code: int = 500) -> dict:
    return {
        "statusCode": status_code,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": content,
    }


def get_logger() -> logging.Logger:
    logging.basicConfig(
        format="[%(asctime)s] %(message)s",
        level=logging.INFO,
        datefmt="%d-%b-%y %H:%M:%S",
    )
    logger = logging.getLogger("mangum")
    logger.setLevel(logging.INFO)
    return logger
