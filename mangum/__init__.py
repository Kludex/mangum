import asyncio
import urllib.parse
import json

from mangum.protocols import ASGIHTTPCycle, ASGIWebSocketCycle


def asgi_handler(app, event, context):

    request_context = event["requestContext"]
    event_type = request_context.get("eventType", None)

    if event_type == "CONNECT" or event_type is None:

        headers = event["headers"] or {}
        host = headers.get("Host")
        scheme = headers.get("X-Forwarded-Proto", "http")
        x_forwarded_port = headers.get("X-Forwarded-Port")

        if not any((host, x_forwarded_port)):
            server = None
        else:
            server = (host, int(x_forwarded_port))

        client = None

        query_string = ""

        if "queryStringParameters" in event:
            query_string_params = event["queryStringParameters"]
            if query_string_params:
                query_string = urllib.parse.urlencode(query_string_params).encode(
                    "ascii"
                )

        scope = {
            "server": server,
            "client": client,
            "scheme": scheme,
            "root_path": "",
            "query_string": query_string,
            "headers": headers.items(),
        }

        if event_type == "CONNECT":
            # WebSocket CONNECT events in AWS need to be responded to before we can
            # use the connection.

            request_context = event["requestContext"]
            event_type = request_context["eventType"]
            # Need to persist this information somehow.
            return {"statusCode": 200, "body": "OK"}

    elif event_type == "MESSAGE":

        # domain_name = request_context["domainName"]
        # stage = request_context["stage"]
        # path = stage  # double-check
        # connection_id = request_context["connectionId"]
        # callback_url = f"https://{domain_name}/{stage}/@connections/{connection_id}"
        # scheme = "wss" if scheme == "https" else "ws"
        # scope.update({"type": "websocket", "scheme": scheme, "path": path})
        # asgi_cycle = ASGIWebSocketCycle(
        #     scope, callback_url=callback_url, connection_id=connection_id
        # )
        # asgi_cycle.put_message({"type": "websocket.connect"})
        return {}

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
