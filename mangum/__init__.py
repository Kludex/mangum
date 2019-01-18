from mangum.handlers import http_handler, websocket_handler


def asgi_handler(app, event: dict, context: dict) -> dict:

    if "httpMethod" in event:
        return http_handler(app, event, context)
    return websocket_handler(app, event, context)
