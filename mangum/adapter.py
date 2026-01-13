from __future__ import annotations

import asyncio
import logging
from itertools import chain
from typing import Any

from mangum._compat import asyncio_run
from mangum.exceptions import ConfigurationError
from mangum.handlers import ALB, APIGateway, HTTPGateway, LambdaAtEdge
from mangum.protocols import HTTPCycle, LifespanCycle
from mangum.types import ASGI, LambdaConfig, LambdaContext, LambdaEvent, LambdaHandler, LifespanMode, LoopFactory

logger = logging.getLogger("mangum")

HANDLERS: list[type[LambdaHandler]] = [ALB, HTTPGateway, APIGateway, LambdaAtEdge]

DEFAULT_TEXT_MIME_TYPES: list[str] = [
    "text/",
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
    "application/vnd.oai.openapi",
]


class Mangum:
    def __init__(
        self,
        app: ASGI,
        lifespan: LifespanMode = "auto",
        api_gateway_base_path: str = "/",
        custom_handlers: list[type[LambdaHandler]] | None = None,
        text_mime_types: list[str] | None = None,
        exclude_headers: list[str] | None = None,
        loop_factory: LoopFactory | None = None,
    ) -> None:
        if lifespan not in ("auto", "on", "off"):
            raise ConfigurationError("Invalid argument supplied for `lifespan`. Choices are: auto|on|off")

        self.app = app
        self.lifespan = lifespan
        self._factory_loop: asyncio.AbstractEventLoop | None = None
        if loop_factory:
            self._factory_loop = loop_factory()
            asyncio.set_event_loop(self._factory_loop)
        self.custom_handlers = custom_handlers or []
        exclude_headers = exclude_headers or []
        self.config = LambdaConfig(
            api_gateway_base_path=api_gateway_base_path or "/",
            text_mime_types=text_mime_types or [*DEFAULT_TEXT_MIME_TYPES],
            exclude_headers=[header.lower() for header in exclude_headers],
        )

    def infer(self, event: LambdaEvent, context: LambdaContext) -> LambdaHandler:
        for handler_cls in chain(self.custom_handlers, HANDLERS):
            if handler_cls.infer(event, context, self.config):
                return handler_cls(event, context, self.config)
        raise RuntimeError(  # pragma: no cover
            "The adapter was unable to infer a handler to use for the event. This "
            "is likely related to how the Lambda function was invoked. (Are you "
            "testing locally? Make sure the request payload is valid for a "
            "supported handler.)"
        )

    def __call__(self, event: LambdaEvent, context: LambdaContext) -> dict[str, Any]:
        async def handle_request() -> dict[str, Any]:
            handler = self.infer(event, context)
            scope = handler.scope

            if self.lifespan in ("auto", "on"):
                lifespan_cycle = LifespanCycle(self.app, self.lifespan)
                async with lifespan_cycle:
                    scope.update({"state": lifespan_cycle.lifespan_state.copy()})
                    http_cycle = HTTPCycle(scope, handler.body)
                    http_response = await http_cycle(self.app)
                    return handler(http_response)
            else:
                http_cycle = HTTPCycle(scope, handler.body)
                http_response = await http_cycle(self.app)
                return handler(http_response)

        if self._factory_loop is not None:
            return self._factory_loop.run_until_complete(handle_request())

        return asyncio_run(handle_request())
