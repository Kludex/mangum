import typing
import logging
import asyncio
from dataclasses import dataclass


@dataclass
class Lifespan:

    app: typing.Any
    logger: logging.Logger
    startup_event: asyncio.Event = asyncio.Event()
    shutdown_event: asyncio.Event = asyncio.Event()
    app_queue: asyncio.Queue = asyncio.Queue()

    async def run(self):
        try:
            await self.app({"type": "lifespan"}, self.receive, self.send)
        except BaseException as exc:  # pragma: no cover
            self.logger.error(f"Exception in 'lifespan' protocol: {exc}")
        finally:
            self.startup_event.set()
            self.shutdown_event.set()

    async def send(self, message: dict) -> None:
        if message["type"] == "lifespan.startup.complete":
            self.startup_event.set()
        elif message["type"] == "lifespan.shutdown.complete":
            self.shutdown_event.set()
        else:  # pragma: no cover
            raise RuntimeError(
                f"Expected lifespan message type, received: {message['type']}"
            )

    async def receive(self) -> dict:
        message = await self.app_queue.get()
        return message

    async def wait_startup(self):
        self.logger.info("Waiting for application startup.")
        await self.app_queue.put({"type": "lifespan.startup"})
        await self.startup_event.wait()

    async def wait_shutdown(self):
        self.logger.info("Waiting for application shutdown.")
        await self.app_queue.put({"type": "lifespan.shutdown"})
        await self.shutdown_event.wait()
