import logging
from itertools import chain
from contextlib import ExitStack
from typing import List, Optional, Type

from mangum.protocols import HTTPCycle, LifespanCycle
from mangum.handlers import ALB, HTTPGateway, APIGateway, LambdaAtEdge
from mangum.exceptions import ConfigurationError
from mangum.types import (
    ASGI,
    LifespanMode,
    LambdaConfig,
    LambdaEvent,
    LambdaContext,
    LambdaHandler,
)


logger = logging.getLogger("mangum")


HANDLERS: List[Type[LambdaHandler]] = [
    ALB,
    HTTPGateway,
    APIGateway,
    LambdaAtEdge,
]


class Mangum:
    def __init__(
        self,
        app: ASGI,
        lifespan: LifespanMode = "auto",
        api_gateway_base_path: str = "/",
        custom_handlers: Optional[List[Type[LambdaHandler]]] = None,
    ) -> None:
        if lifespan not in ("auto", "on", "off"):
            raise ConfigurationError(
                "Invalid argument supplied for `lifespan`. Choices are: auto|on|off"
            )

        self.app = app
        self.lifespan = lifespan
        self.api_gateway_base_path = api_gateway_base_path or "/"
        self.config = LambdaConfig(api_gateway_base_path=self.api_gateway_base_path)
        self.custom_handlers = custom_handlers or []

    def infer(self, event: LambdaEvent, context: LambdaContext) -> LambdaHandler:
        for handler_cls in chain(self.custom_handlers, HANDLERS):
            if handler_cls.infer(event, context, self.config):
                handler = handler_cls(event, context, self.config)
                break
        else:
            raise RuntimeError(  # pragma: no cover
                "The adapter was unable to infer a handler to use for the event. This "
                "is likely related to how the Lambda function was invoked. (Are you "
                "testing locally? Make sure the request payload is valid for a "
                "supported handler.)"
            )

        return handler

    def __call__(self, event: LambdaEvent, context: LambdaContext) -> dict:
        handler = self.infer(event, context)
        with ExitStack() as stack:
            if self.lifespan in ("auto", "on"):
                lifespan_cycle = LifespanCycle(self.app, self.lifespan)
                stack.enter_context(lifespan_cycle)

            http_cycle = HTTPCycle(handler.scope, handler.body)
            http_response = http_cycle(self.app)

            return handler(http_response)

        assert False, "unreachable"  # pragma: no cover
