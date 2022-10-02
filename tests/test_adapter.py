import pytest

from mangum import Mangum
from mangum.adapter import DEFAULT_TEXT_MIME_TYPES
from mangum.exceptions import ConfigurationError


async def app(scope, receive, send):
    ...


def test_default_settings():
    handler = Mangum(app)
    assert handler.lifespan == "auto"
    assert handler.api_gateway_base_path == "/"
    assert sorted(handler.text_mime_types) == sorted(DEFAULT_TEXT_MIME_TYPES)


def test_default_settings_mutation():
    handler = Mangum(app)

    # API gateway base path
    assert handler.api_gateway_base_path == "/"
    new_base_path = "/prefix/"
    handler.api_gateway_base_path = new_base_path
    assert (
        handler.api_gateway_base_path
        == handler.config["api_gateway_base_path"]
        == new_base_path
    )


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
