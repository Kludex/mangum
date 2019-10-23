import base64
import asyncio
import traceback
import urllib.parse
import typing
import json
import logging
from dataclasses import dataclass

from mangum.lifespan import Lifespan
from mangum.utils import get_logger, make_response, get_server_and_client
from mangum.types import ASGIApp, AWSMessage


@dataclass
class Mangum:

    app: ASGIApp
    debug: bool = False
    enable_lifespan: bool = True
    log_level: str = "info"

    def __post_init__(self) -> None:
        self.logger = get_logger(log_level=self.log_level)
        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            self.lifespan = Lifespan(self.app, logger=self.logger)
            loop.create_task(self.lifespan.run())
            loop.run_until_complete(self.lifespan.wait_startup())

    def __call__(self, event: AWSMessage, context: AWSMessage) -> AWSMessage:
        try:
            response = self.handler(event, context)
        except Exception as exc:
            if self.debug:
                content = traceback.format_exc()
                return make_response(content, status_code=500)
            raise exc
        else:
            return response

    def handler(self, event: AWSMessage, context: AWSMessage) -> AWSMessage:
        if "httpMethod" in event:
            from mangum.protocols.http import handle_http

            response = handle_http(self.app, event, context)
        else:
            try:
                from mangum.protocols.websockets import handle_ws
            except ImportError as exc:  # pragma: nocover
                raise exc

            response = handle_ws(self.app, event, context)

        if self.enable_lifespan:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.lifespan.wait_shutdown())
        return response
