import logging
import typing
import urllib.parse
from dataclasses import dataclass

from mangum.types import Scope


DEFAULT_TEXT_MIME_TYPES = [
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
]


def get_logger(log_level: str) -> logging.Logger:
    """
    Create the default logger according to log level setting of the adapter instance.
    """
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


def get_server_and_headers(event: dict) -> typing.Tuple:  # pragma: no cover
    headers = (
        {k.lower(): v for k, v in event.get("headers").items()}  # type: ignore
        if event.get("headers")
        else {}
    )

    server_name = headers.get("host", "mangum")
    if ":" not in server_name:
        server_port = headers.get("x-forwarded-port", 80)
    else:
        server_name, server_port = server_name.split(":")
    server = (server_name, int(server_port))

    return server, headers


@dataclass
class Config:
    """
    Manages the configuration for an adapter instance.
    """

    lifespan: str
    log_level: str
    api_gateway_base_path: typing.Optional[str]
    text_mime_types: typing.Optional[typing.List[str]]
    dsn: typing.Optional[str]
    api_gateway_endpoint_url: typing.Optional[str]
    api_gateway_region_name: typing.Optional[str]

    def __post_init__(self) -> None:
        self.logger: logging.Logger = get_logger(self.log_level)
        if self.api_gateway_base_path:
            self.api_gateway_base_path = f"/{self.api_gateway_base_path}"
        if self.text_mime_types:
            self.text_mime_types = self.text_mime_types + DEFAULT_TEXT_MIME_TYPES
        else:
            self.text_mime_types = DEFAULT_TEXT_MIME_TYPES

    def make_http_scope(self, event: dict, context: dict) -> Scope:
        request_context = event["requestContext"]
        if "http" in request_context:
            source_ip = request_context["http"]["sourceIp"]
            path = request_context["http"]["path"]
            http_method = request_context["http"]["method"]
            query_string = event.get("rawQueryString", "").encode()
        else:
            source_ip = request_context.get("identity", {}).get("sourceIp")
            multi_value_query_string_params = event["multiValueQueryStringParameters"]
            query_string = (
                urllib.parse.urlencode(
                    multi_value_query_string_params, doseq=True
                ).encode()
                if multi_value_query_string_params
                else b""
            )
            path = event["path"]
            http_method = event["httpMethod"]

        server, headers = get_server_and_headers(event)
        client = (source_ip, 0)

        if not path:  # pragma: no cover
            path = "/"
        elif self.api_gateway_base_path:
            if path.startswith(self.api_gateway_base_path):
                path = path[len(self.api_gateway_base_path) :]

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": http_method,
            "headers": [[k.encode(), v.encode()] for k, v in headers.items()],
            "path": urllib.parse.unquote(path),
            "raw_path": None,
            "root_path": "",
            "scheme": headers.get("x-forwarded-proto", "https"),
            "query_string": query_string,
            "server": server,
            "client": client,
            "asgi": {"version": "3.0"},
            "aws.event": event,
            "aws.context": context,
        }

        return scope

    def make_websocket_scope(self, event: dict) -> Scope:
        server, headers = get_server_and_headers(event)
        source_ip = event["requestContext"].get("identity", {}).get("sourceIp")
        client = (source_ip, 0)

        scope = {
            "type": "websocket",
            "path": "/",
            "headers": headers,
            "raw_path": None,
            "root_path": "",
            "scheme": headers.get("x-forwarded-proto", "wss"),
            "query_string": "",
            "server": server,
            "client": client,
            "asgi": {"version": "3.0"},
            "aws.event": event,
        }

        return scope
