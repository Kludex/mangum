import pytest

from mangum import Mangum
from mangum.adapter import DEFAULT_TEXT_MIME_TYPES
from mangum.exceptions import ConfigurationError


async def app(scope, receive, send):
    ...


def test_default_settings():
    handler = Mangum(app)
    assert handler.lifespan == "auto"
    assert handler.config["api_gateway_base_path"] == "/"
    assert sorted(handler.config["text_mime_types"]) == sorted(DEFAULT_TEXT_MIME_TYPES)


@pytest.mark.parametrize(
    "arguments,message",
    [
        (
            {"lifespan": "unknown"},
            "Invalid argument supplied for `lifespan`. Choices are: auto|on|off",
        ),
    ],
)
def test_invalid_options(arguments, message):
    with pytest.raises(ConfigurationError) as exc:
        Mangum(app, **arguments)

    assert str(exc.value) == message
