import base64
from typing import Any, Callable, ContextManager, Dict, Optional, List, TYPE_CHECKING
import logging
import urllib.parse

from dataclasses import dataclass, InitVar
from contextlib import ExitStack

from mangum.handlers import AbstractHandler
from mangum.response import Response
from mangum.types import ASGIApp, ScopeDict
from mangum.protocols.lifespan import LifespanCycle
from mangum.protocols.http import HTTPCycle
from mangum.exceptions import ConfigurationError

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
        **handler_kwargs,
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
            http_cycle = HTTPCycle(handler.scope.as_dict())
            response = http_cycle(self.app, handler.body)

        return handler.transform_response(response)
