from mangum.platforms.aws.adapter import run_asgi


class AWSLambdaMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    def __call__(self, event, context):
        return run_asgi(self.app, event, context)
