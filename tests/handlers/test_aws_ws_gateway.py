from mangum import Mangum


def test_aws_ws_gateway_scope(
    sqlite3_dsn, mock_ws_connect_event, mock_ws_send_event, mock_ws_disconnect_event
):
    def make_app(event):
        async def wrapped(scope, receive, send):
            assert scope == {
                "asgi": {"version": "3.0"},
                "aws.context": {},
                "aws.event": event,
                "aws.eventType": "AWS_WS_GATEWAY",
                "client": ("192.168.100.1", 0),
                "headers": [
                    [b"accept-encoding", b"gzip, deflate, br"],
                    [b"accept-language", b"en-US,en;q=0.9"],
                    [b"cache-control", b"no-cache"],
                    [b"host", b"test.execute-api.ap-southeast-1.amazonaws.com"],
                    [
                        b"origin",
                        b"https://test.execute-api.ap-southeast-1.amazonaws.com",
                    ],
                    [b"pragma", b"no-cache"],
                    [
                        b"sec-websocket-extensions",
                        b"permessage-deflate; client_max_window_bits",
                    ],
                    [b"sec-websocket-key", b"bnfeqmh9SSPr5Sg9DvFIBw=="],
                    [b"sec-websocket-version", b"13"],
                    [
                        b"user-agent",
                        b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) "
                        b"AppleWebKit/537.36 (KHTML, like Gecko) "
                        b"Chrome/75.0.3770.100 Safari/537.36",
                    ],
                    [b"x-amzn-trace-id", b"Root=1-5d465cb6-78ddcac1e21f89203d004a89"],
                    [b"x-forwarded-for", b"192.168.100.1"],
                    [b"x-forwarded-port", b"443"],
                    [b"x-forwarded-proto", b"https"],
                ],
                "http_version": "1.1",
                "path": "/",
                "query_string": b"",
                "raw_path": None,
                "root_path": "",
                "scheme": "https",
                "server": ("test.execute-api.ap-southeast-1.amazonaws.com", 443),
                "subprotocols": [],
                "type": "websocket",
            }

        return wrapped

    app = make_app(mock_ws_connect_event)
    handler = Mangum(app, lifespan="off", dsn=sqlite3_dsn)
    response = handler(mock_ws_connect_event, {})
    assert response == {"statusCode": 200}

    app = make_app(mock_ws_send_event)
    handler = Mangum(app, lifespan="off", dsn=sqlite3_dsn)
    response = handler(mock_ws_send_event, {})
    assert response == {"statusCode": 200}

    app = make_app(mock_ws_disconnect_event)
    handler = Mangum(app, lifespan="off", dsn=sqlite3_dsn)
    response = handler(mock_ws_disconnect_event, {})
    assert response == {"statusCode": 200}
