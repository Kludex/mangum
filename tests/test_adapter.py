import asyncio
import threading
from typing import Any

import pytest

from mangum import Mangum
from mangum.adapter import DEFAULT_TEXT_MIME_TYPES
from mangum.exceptions import ConfigurationError
from mangum.types import Receive, Scope, Send


async def app(scope: Scope, receive: Receive, send: Send) -> None: ...


def test_default_settings() -> None:
    handler = Mangum(app)
    assert handler.lifespan == "auto"
    assert handler.config["api_gateway_base_path"] == "/"
    assert sorted(handler.config["text_mime_types"]) == sorted(DEFAULT_TEXT_MIME_TYPES)
    assert handler.config["exclude_headers"] == []


@pytest.mark.parametrize(
    "arguments,message",
    [
        (
            {"lifespan": "unknown"},
            "Invalid argument supplied for `lifespan`. Choices are: auto|on|off",
        ),
    ],
)
def test_invalid_options(arguments: dict[str, Any], message: str) -> None:
    with pytest.raises(ConfigurationError) as exc:
        Mangum(app, **arguments)

    assert str(exc.value) == message


def test_event_loop_created_when_missing() -> None:
    result: dict[str, Mangum] = {}

    def create_handler() -> None:
        result["handler"] = Mangum(app)
        asyncio.get_event_loop().close()

    thread = threading.Thread(target=create_handler)
    thread.start()
    thread.join()

    assert result["handler"].lifespan == "auto"


def test_event_loop_reused_when_present() -> None:
    loop = asyncio.new_event_loop()

    def create_handler() -> None:
        asyncio.set_event_loop(loop)
        Mangum(app)

    thread = threading.Thread(target=create_handler)
    thread.start()
    thread.join()

    loop.close()
