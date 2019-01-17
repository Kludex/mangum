import asyncio
import urllib.parse


from mangum.protocols import ASGIHTTPCycle, ASGIWebSocketCycle


def asgi_handler(app, event, context):
    headers = event["headers"] or {}
    host = headers.get("Host")
    scheme = headers.get("X-Forwarded-Proto", "http")
    x_forwarded_port = headers.get("X-Forwarded-Port")

    if not any((host, x_forwarded_port)):
        server = None
    else:
        server = (host, int(x_forwarded_port))

    client = None  # client = headers.get("X-Forwarded-For", None)

    query_string_params = event["queryStringParameters"]
    if query_string_params:
        query_string = urllib.parse.urlencode(query_string_params).encode("ascii")
    else:
        query_string = ""

    scope = {
        "server": server,
        "client": client,
        "scheme": scheme,
        "root_path": "",
        "query_string": query_string,
        "headers": headers.items(),
    }

    is_websocket = "Sec-WebSocket-Key" in headers

    loop = asyncio.get_event_loop()

    if not is_websocket:
        method = event["httpMethod"]
        path = event["path"]
        body = b""
        more_body = False
        # body = event.get("body", b"")
        # more_body = False
        # if body and event.get("isBase64Encoded"):
        #     body = base64.standard_b64decode(body)
        scope.update(
            {"type": "http", "http_version": "1.1", "method": method, "path": path}
        )
        asgi_cycle = ASGIHTTPCycle(scope)
        asgi_cycle.put_message(
            {"type": "http.request", "body": body, "more_body": more_body}
        )

    else:
        request_context = event["requestContext"]
        route_key = request_context["routeKey"]
        connection_id = request_context["connectionId"]
        # headers["Sec-WebSocket-Extensions"] # ["permessage-deflate; " "client_max_window_bits"]
        # headers["Sec-WebSocket-Key"] # ["XXXXX"],
        # endpoint = f"{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
        subprotocols = None
        scheme = "wss" if scheme == "https" else "ws"
        scope.update(
            {"type": "websocket", "scheme": scheme, "subprotocols": subprotocols}
        )
        asgi_cycle = ASGIWebSocketCycle(scope)
        asgi_cycle.put_message({"type": "websocket.connect"})

    asgi_instance = app(asgi_cycle.scope)
    asgi_task = loop.create_task(asgi_instance(asgi_cycle.receive, asgi_cycle.send))
    loop.run_until_complete(asgi_task)

    return asgi_cycle.response
