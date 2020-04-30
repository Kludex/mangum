import asyncio
import logging
from dataclasses import dataclass

from mangum.types import ASGIApp, Message
from mangum.exceptions import LifespanFailure


@dataclass
class Lifespan:
    app: ASGIApp
    is_supported: bool = False
    has_error: bool = False

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.lifespan")
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.startup_event: asyncio.Event = asyncio.Event()
        self.shutdown_event: asyncio.Event = asyncio.Event()

    async def startup(self) -> None:
        if self.is_supported:
            self.logger.info("Waiting for application startup.")
            await self.app_queue.put({"type": "lifespan.startup"})
            await self.startup_event.wait()
            if self.has_error:
                self.logger.error("Application startup failed.")
            else:
                self.logger.info("Application startup complete.")

    async def shutdown(self) -> None:
        if self.has_error:
            return
        self.logger.info("Waiting for application shutdown.")
        await self.app_queue.put({"type": "lifespan.shutdown"})
        await self.shutdown_event.wait()

    async def run(self) -> None:
        try:
            await self.app({"type": "lifespan"}, self.receive, self.send)
        except BaseException as exc:
            self.startup_event.set()
            self.shutdown_event.set()
            self.has_error = True
            if not self.is_supported:
                self.logger.info("ASGI 'lifespan' protocol appears unsupported.")
            else:
                self.logger.error("Exception in 'lifespan' protocol.", exc_info=exc)

    async def receive(self) -> Message:
        self.is_supported = True

        return await self.app_queue.get()

    async def send(self, message: Message) -> None:
        if not self.is_supported:
            raise LifespanFailure("Lifespan unsupported.")

        message_type = message["type"]
        if message_type == "lifespan.startup.complete":
            self.startup_event.set()
        elif message_type == "lifespan.shutdown.complete":
            self.shutdown_event.set()
        else:
            raise RuntimeError(
                f"Expected lifespan message type, received: {message_type}"
            )
