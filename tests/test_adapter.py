import asyncio
from unittest.mock import patch

import pytest

from mangum import Mangum
from mangum.adapter import DEFAULT_TEXT_MIME_TYPES
from mangum.exceptions import ConfigurationError
from mangum.types import Receive, Scope, Send


async def app(scope: Scope, receive: Receive, send: Send): ...


def test_default_settings():
    handler = Mangum(app)
    assert handler.lifespan == 'auto'
    assert handler.config['api_gateway_base_path'] == '/'
    assert sorted(handler.config['text_mime_types']) == sorted(DEFAULT_TEXT_MIME_TYPES)
    assert handler.config['exclude_headers'] == []


@pytest.mark.parametrize(
    'arguments,message',
    [
        (
            {'lifespan': 'unknown'},
            'Invalid argument supplied for `lifespan`. Choices are: auto|on|off',
        ),
    ],
)
def test_invalid_options(arguments, message):
    with pytest.raises(ConfigurationError) as exc:
        Mangum(app, **arguments)

    assert str(exc.value) == message


@pytest.mark.parametrize('mock_aws_api_gateway_event', [['GET', None, None]], indirect=True)
def test_loop_factory_reuses_loop(mock_aws_api_gateway_event):
    """Loop is not closed between invocations when loop_factory is provided."""
    loop = asyncio.new_event_loop()

    async def app(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'OK'})

    handler = Mangum(app, lifespan='off', loop_factory=lambda: loop)

    try:
        handler(mock_aws_api_gateway_event, {})
        handler(mock_aws_api_gateway_event, {})
        assert not loop.is_closed()
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.mark.parametrize('mock_aws_api_gateway_event', [['GET', None, None]], indirect=True)
def test_loop_factory_sets_current_loop(mock_aws_api_gateway_event):
    """loop_factory sets the loop as current."""
    loop = asyncio.new_event_loop()

    async def app(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'OK'})

    handler = Mangum(app, lifespan='off', loop_factory=lambda: loop)

    try:
        with patch('asyncio.set_event_loop') as mock_set:
            handler(mock_aws_api_gateway_event, {})
            mock_set.assert_called_with(loop)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.mark.parametrize('mock_aws_api_gateway_event', [['GET', None, None]], indirect=True)
def test_loop_factory_bypasses_asyncio_run(mock_aws_api_gateway_event):
    """asyncio_run is not called when loop_factory is provided."""
    loop = asyncio.new_event_loop()

    async def app(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'OK'})

    handler = Mangum(app, lifespan='off', loop_factory=lambda: loop)

    try:
        with patch('mangum.adapter.asyncio_run') as mock:
            handler(mock_aws_api_gateway_event, {})
            mock.assert_not_called()
    finally:
        loop.close()
        asyncio.set_event_loop(None)
