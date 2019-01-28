from mangum.platforms.aws.adapter import AWSLambdaAdapter
from yourapp.app import app


handler = AWSLambdaAdapter(app)  # optionally set debug=True
