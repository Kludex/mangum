import logging
from pprint import pformat
from mangum.handlers import http_handler


logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)
logger = logging.getLogger("mangum")
logger.setLevel(logging.DEBUG)


def asgi_handler(app, event: dict, context: dict) -> dict:
    logger.debug(pformat(event))
    if "httpMethod" in event:
        return http_handler(app, event, context)
