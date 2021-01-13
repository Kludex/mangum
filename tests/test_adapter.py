import pytest

from mangum.exceptions import ConfigurationError
from mangum.adapter import DEFAULT_TEXT_MIME_TYPES
from mangum import Mangum


async def app(scope, receive, send):
    ...


def test_default_settings():
    handler = Mangum(app)
    assert handler.lifespan == "auto"
    assert handler.log_level == "info"
    assert handler.text_mime_types == DEFAULT_TEXT_MIME_TYPES
    assert handler.api_gateway_base_path is None


@pytest.mark.parametrize(
    "arguments,message",
    [
        (
            {"lifespan": "unknown"},
            "Invalid argument supplied for `lifespan`. Choices are: auto|on|off",
        ),
        (
            {"log_level": "unknown"},
            "Invalid argument supplied for `log_level`. Choices are: "
            "critical|error|warning|info|debug",
        ),
    ],
)
def test_invalid_options(arguments, message):
    with pytest.raises(ConfigurationError) as exc:
        Mangum(app, **arguments)

    assert str(exc.value) == message
