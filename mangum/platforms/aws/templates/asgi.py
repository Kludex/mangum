from mangum.platforms.aws.middleware import AWSLambdaMiddleware

# from <yourapp> import app


def lambda_handler(event, context):
    return AWSLambdaMiddleware(app)(event, context)
