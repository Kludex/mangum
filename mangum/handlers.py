import asyncio
import urllib.parse
from mangum.protocols.http import ASGIHTTPCycle


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
