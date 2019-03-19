import pytest
from mangum import Mangum


def test_asgi_cycle_state(mock_data) -> None:
    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.body", "body": b"Hello, world!"})

        return asgi

    mock_event = mock_data.get_aws_event()
    with pytest.raises(RuntimeError):
        Mangum(app)(mock_event, {})

    def app(scope):
        async def asgi(receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.start", "status": 200, "headers": []})

        return asgi

    mock_event = mock_data.get_aws_event()
    with pytest.raises(RuntimeError):
        Mangum(app)(mock_event, {})


def test_asgi_spec_version(mock_data) -> None:
    async def app(scope, receive, send):
        assert scope["type"] == "http"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"Hello, world!"})

    mock_event = mock_data.get_aws_event()
    handler = Mangum(app, spec_version=3)
    response = handler(mock_event, {})

    assert response == {
        "statusCode": 200,
        "isBase64Encoded": False,
        "headers": {},
        "body": "Hello, world!",
    }
