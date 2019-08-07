import logging
import os

import boto3


def get_connections():
    db = boto3.resource("dynamodb")
    connections = db.Table(os.environ["TABLE_NAME"])
    return connections


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
