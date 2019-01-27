from mangum.platforms.aws.middleware import AWSLambdaMiddleware
from ASGIApp.app import app


def lambda_handler(event, context):
    return AWSLambdaMiddleware(app)(event, context)
    # return run_asgi(app, event, context)
