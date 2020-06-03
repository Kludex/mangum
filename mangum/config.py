import logging
import typing
import os
from dataclasses import dataclass


from mangum.exceptions import ConfigurationError

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
    broadcast: bool

    def __post_init__(self) -> None:
        self.logger: logging.Logger = get_logger(self.log_level)
        if self.api_gateway_base_path:
            self.api_gateway_base_path = f"/{self.api_gateway_base_path}"
        if self.text_mime_types:
            self.text_mime_types = self.text_mime_types + DEFAULT_TEXT_MIME_TYPES
        else:
            self.text_mime_types = DEFAULT_TEXT_MIME_TYPES

    def update(self, request_context: dict) -> None:
        event_type = request_context.get("eventType")
        if event_type:
            if self.dsn is None:
                raise ConfigurationError(
                    "A `dsn` connection string is required for WebSocket support."
                )
            self.connection_id: str = request_context["connectionId"]
            if not self.api_gateway_endpoint_url:
                self.api_gateway_endpoint_url = f"https://{request_context['domainName']}/{request_context['stage']}"

            if not self.api_gateway_region_name:
                self.api_gateway_region_name = os.environ["AWS_REGION"]

            if event_type in ("CONNECT", "DISCONNECT"):
                self.lifespan: str = "off"
            self.api_gateway_event_type = event_type

        elif "http" in request_context:
            self.api_gateway_event_type = "HTTP"
        else:
            self.api_gateway_event_type = "REST"
