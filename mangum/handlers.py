import asyncio
import urllib.parse

from mangum.protocols.http import ASGIHTTPCycle
from mangum.protocols.websockets import ASGIWebSocketCycle


def get_scope(event: dict) -> dict:
    headers = event["headers"] or {}
    host = headers.get("Host")
    scheme = headers.get("X-Forwarded-Proto", "http")
    x_forwarded_for = headers.get("X-Forwarded-For")
    x_forwarded_port = headers.get("X-Forwarded-Port")
    client = None
    server = None

    if x_forwarded_port and x_forwarded_for:
        port = int(x_forwarded_port)
        client = (x_forwarded_for, port)
        if host:
            server = (host, port)

    query_string = ""
    if "queryStringParameters" in event:
        query_string_params = event["queryStringParameters"]
        if query_string_params:
            query_string = urllib.parse.urlencode(query_string_params).encode("ascii")

    scope = {
        "server": server,
        "client": client,
        "scheme": scheme,
        "root_path": "",
        "query_string": query_string,
        "headers": headers.items(),
    }

    return scope


def http_handler(app, event: dict, context: dict) -> dict:
    scope = get_scope(event)
    scope.update(
        {
            "type": "http",
            "http_version": "1.1",
            "method": event["httpMethod"],
            "path": event["path"],
        }
    )

    body = b""
    more_body = False

    loop = asyncio.get_event_loop()
    asgi_cycle = ASGIHTTPCycle(scope)
    asgi_cycle.put_message(
        {"type": "http.request", "body": body, "more_body": more_body}
    )
    asgi_instance = app(asgi_cycle.scope)
    asgi_task = loop.create_task(asgi_instance(asgi_cycle.receive, asgi_cycle.send))
    loop.run_until_complete(asgi_task)

    return asgi_cycle.response


def websocket_handler(app, event: dict, context: dict) -> dict:
    request_context = event["requestContext"]
    event_type = request_context["eventType"]

    if event_type == "CONNECT":
        # WebSocket CONNECT events in AWS need to be responded to before we can
        # use the connection. Need to persist this information somehow...

        scope = get_scope(event)

        domain_name = request_context["domainName"]
        stage = request_context["stage"]
        path = stage  # double-check
        connection_id = request_context["connectionId"]
        callback_url = f"https://{domain_name}/{stage}/@connections/{connection_id}"

        scheme = "wss" if scope["scheme"] == "https" else "ws"
        scope.update({"type": "websocket", "scheme": scheme, "path": path})

        return {"statusCode": 200, "body": "OK"}

    if event_type == "MESSAGE":

        # asgi_cycle = ASGIWebSocketCycle(
        #     scope, callback_url=callback_url, connection_id=connection_id
        # )
        # asgi_cycle.put_message({"type": "websocket.connect"})
        return {}
