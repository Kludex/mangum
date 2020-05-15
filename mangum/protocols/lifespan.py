import asyncio
import logging
import types
import typing
import enum
from dataclasses import dataclass

from mangum.types import ASGIApp, Message
from mangum.exceptions import LifespanUnsupported, LifespanFailure, UnexpectedMessage


class LifespanCycleState(enum.Enum):
    CONNECTING = enum.auto()
    STARTUP = enum.auto()
    SHUTDOWN = enum.auto()
    FAILED = enum.auto()
    UNSUPPORTED = enum.auto()


@dataclass
class LifespanCycle:
    app: ASGIApp
    lifespan: str
    state: LifespanCycleState = LifespanCycleState.CONNECTING
    exception: typing.Optional[BaseException] = None

    def __post_init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.lifespan")
        self.loop = asyncio.get_event_loop()
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.startup_event: asyncio.Event = asyncio.Event()
        self.shutdown_event: asyncio.Event = asyncio.Event()

    def __enter__(self) -> None:
        """
        Runs the event loop for application startup.
        """
        self.loop.create_task(self.run())
        self.loop.run_until_complete(self.startup())

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_value: typing.Optional[BaseException],
        traceback: typing.Optional[types.TracebackType],
    ) -> None:
        """
        Runs the event loop for application shutdown.
        """
        self.loop.run_until_complete(self.shutdown())

    async def run(self) -> None:
        """
        Calls the application with the connection scope, handling error cases.
        """
        try:
            await self.app({"type": "lifespan"}, self.receive, self.send)
        except LifespanUnsupported:
            self.logger.info("ASGI 'lifespan' protocol appears unsupported.")
        except (LifespanFailure, UnexpectedMessage) as exc:
            self.exception = exc
        except BaseException as exc:
            self.logger.error("Exception in 'lifespan' protocol.", exc_info=exc)
        finally:
            self.startup_event.set()
            self.shutdown_event.set()

    async def receive(self) -> Message:
        """
        Awaited by the application to receive ASGI lifespan events, handling event
        state transitions.
        """
        if self.state is LifespanCycleState.CONNECTING:

            # Connection established. The next event returned by the queue will be
            # `lifespan.startup` to inform the application that the connection is
            # ready to receive lfiespan messages.
            self.state = LifespanCycleState.STARTUP

        elif self.state is LifespanCycleState.STARTUP:

            # Connection shutting down. The next event returned by the queue will be
            # `lifespan.shutdown` to inform the application that the connection is now
            # closing so that it may perform cleanup.
            self.state = LifespanCycleState.SHUTDOWN

        return await self.app_queue.get()

    async def send(self, message: Message) -> None:
        """
        Awaited by the application to send ASGI lifespan events.
        """
        message_type = message["type"]
        self.logger.info(
            "%s:  '%s' event received from application.", self.state, message_type
        )

        if self.state is LifespanCycleState.CONNECTING:

            if self.lifespan == "on":
                raise LifespanFailure(
                    "Lifespan connection failed during startup and lifespan is 'on'."
                )

            # If a message is sent before the startup event is received by the
            # application, then assume that lifespan is unsupported.
            self.state = LifespanCycleState.UNSUPPORTED
            raise LifespanUnsupported("Lifespan protocol appears unsupported.")

        if message_type not in (
            "lifespan.startup.complete",
            "lifespan.shutdown.complete",
            "lifespan.startup.failed",
            "lifespan.shutdown.failed",
        ):
            self.state = LifespanCycleState.FAILED
            raise UnexpectedMessage(f"Unexpected '{message_type}' event received.")

        if self.state is LifespanCycleState.STARTUP:
            if message_type == "lifespan.startup.complete":
                self.startup_event.set()
            elif message_type == "lifespan.startup.failed":
                self.state = LifespanCycleState.FAILED
                self.startup_event.set()
                message = message.get("message", "")
                raise LifespanFailure(f"Lifespan startup failure. {message}")

        elif self.state is LifespanCycleState.SHUTDOWN:
            if message_type == "lifespan.shutdown.complete":
                self.shutdown_event.set()
            elif message_type == "lifespan.shutdown.failed":
                self.state = LifespanCycleState.FAILED
                self.shutdown_event.set()
                message = message.get("message", "")
                raise LifespanFailure(f"Lifespan shutdown failure. {message}")

    async def startup(self) -> None:
        """
        Sends lifespan startup event to application and handle startup errors.
        """
        self.logger.info("Waiting for application startup.")
        await self.app_queue.put({"type": "lifespan.startup"})
        await self.startup_event.wait()
        if self.state is LifespanCycleState.FAILED:
            raise LifespanFailure(self.exception)

        if not self.exception:
            self.logger.info("Application startup complete.")
        else:
            self.logger.info("Application startup failed.")

    async def shutdown(self) -> None:
        """
        Sends lifespan shutdown event to application and handle shutdown errors.
        """
        self.logger.info("Waiting for application shutdown.")
        await self.app_queue.put({"type": "lifespan.shutdown"})
        await self.shutdown_event.wait()
        if self.state is LifespanCycleState.FAILED:
            raise LifespanFailure(self.exception)
