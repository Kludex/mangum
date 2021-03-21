import logging
from contextlib import ExitStack
from typing import Any, ContextManager, Dict, TYPE_CHECKING

from .exceptions import ConfigurationError
from .handlers import AbstractHandler
from .protocols import HTTPCycle, LifespanCycle
from .types import ASGIApp

if TYPE_CHECKING:  # pragma: no cover
    from awslambdaric.lambda_context import LambdaContext

DEFAULT_TEXT_MIME_TYPES = [
    "text/",
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
]

logger = logging.getLogger("mangum")


class Mangum:
    """
    Creates an adapter instance.

    * **app** - An asynchronous callable that conforms to version 3.0 of the ASGI
    specification. This will usually be an ASGI framework application instance.
    * **lifespan** - A string to configure lifespan support. Choices are `auto`, `on`,
    and `off`. Default is `auto`.
    * **log_level** - A string to configure the log level. Choices are: `info`,
    `critical`, `error`, `warning`, and `debug`. Default is `info`.
    * **text_mime_types** - A list of MIME types to include with the defaults that
    should not return a binary response in API Gateway.
    """

    app: ASGIApp
    lifespan: str = "auto"

    def __init__(
        self,
        app: ASGIApp,
        lifespan: str = "auto",
        **handler_kwargs: Dict[str, Any],
    ):
        self.app = app
        self.lifespan = lifespan
        self.handler_kwargs = handler_kwargs

        if self.lifespan not in ("auto", "on", "off"):
            raise ConfigurationError(
                "Invalid argument supplied for `lifespan`. Choices are: auto|on|off"
            )

    def __call__(self, event: dict, context: "LambdaContext") -> dict:
        logger.debug("Event received.")

        with ExitStack() as stack:
            if self.lifespan != "off":
                lifespan_cycle: ContextManager = LifespanCycle(self.app, self.lifespan)
                stack.enter_context(lifespan_cycle)

            handler = AbstractHandler.from_trigger(
                event, context, **self.handler_kwargs
            )
            http_cycle = HTTPCycle(handler.scope)
            response = http_cycle(self.app, handler.body)

        return handler.transform_response(response)
