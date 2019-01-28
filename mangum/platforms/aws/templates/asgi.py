from mangum.platforms.aws.middleware import AWSLambdaMiddleware
from yourapp.app import app


handler = AWSLambdaMiddleware(app)  # optionally set debug=True
