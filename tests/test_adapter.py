import pytest

from mangum.exceptions import ConfigurationError
from mangum import Mangum


async def app(scope, receive, send):
    ...


def test_default_settings():
    handler = Mangum(app)
    assert handler.lifespan == "auto"


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
