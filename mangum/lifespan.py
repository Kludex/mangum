import logging
import asyncio
from dataclasses import dataclass

from mangum.types import ASGIApp, Message, Send, Receive


@dataclass
class Lifespan:
    app: ASGIApp
    logger: logging.Logger
    startup_event: asyncio.Event = asyncio.Event()
    shutdown_event: asyncio.Event = asyncio.Event()
    app_queue: asyncio.Queue = asyncio.Queue()

    async def run(self) -> None:
        receive, send = (self.receiver(), self.sender())
        try:
            await self.app({"type": "lifespan"}, receive, send)
        except BaseException as exc:  # pragma: no cover
            self.logger.error(f"Exception in 'lifespan' protocol: {exc}")
        finally:
            self.startup_event.set()
            self.shutdown_event.set()

    def sender(self) -> Send:
        # startup_event, shutdown_event = self.startup_event, self.shutdown_event

        async def send(message: Message) -> None:
            message_type = message["type"]
            if message_type == "lifespan.startup.complete":
                self.startup_event.set()
            elif message_type == "lifespan.shutdown.complete":
                self.shutdown_event.set()
            else:  # pragma: no cover
                raise RuntimeError(
                    f"Expected lifespan message type, received: {message_type}"
                )
            return None

        return send

    def receiver(self) -> Receive:
        async def receive() -> Message:
            return await self.app_queue.get()

        return receive

    async def wait_startup(self) -> None:
        self.logger.info("Waiting for application startup.")
        await self.app_queue.put({"type": "lifespan.startup"})
        await self.startup_event.wait()

    async def wait_shutdown(self) -> None:
        self.logger.info("Waiting for application shutdown.")
        await self.app_queue.put({"type": "lifespan.shutdown"})
        await self.shutdown_event.wait()
