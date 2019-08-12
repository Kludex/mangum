import logging


def make_response(content: str, status_code: int = 500) -> dict:
    return {
        "statusCode": status_code,
        "isBase64Encoded": False,
        "headers": {"content-type": "text/plain; charset=utf-8"},
        "body": content,
    }


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
