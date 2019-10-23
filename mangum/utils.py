import logging
import typing


def make_response(content: str, status_code: int = 500) -> dict:
    return {
        "statusCode": status_code,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": content,
    }


def get_server_and_client(
    event: typing.Dict[str, typing.Any]
) -> typing.Tuple:  # pragma: no cover
    """
    Parse the server and client for the scope definition, if possible.
    """
    client_addr = event["requestContext"].get("identity", {}).get("sourceIp", None)
    client = (client_addr, 0)
    server_addr = event["headers"].get("Host", None)

    if server_addr is not None:
        if ":" not in server_addr:
            server_port = 80
        else:
            server_addr, server_port = server_addr.split(":")
            server_port = int(server_port)

        server = (server_addr, server_port)
    else:
        server = None
    return server, client


def get_logger(log_level: str) -> logging.Logger:
    level = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }[log_level]
    logging.basicConfig(
        format="[%(asctime)s] %(message)s", level=level, datefmt="%d-%b-%y %H:%M:%S"
    )
    logger = logging.getLogger("mangum")
    logger.setLevel(level)
    return logger
