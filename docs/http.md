# HTTP

Mangum provides support for the following AWS HTTP Lambda Event Source:

 * [API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html)
   ([Event Examples](https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html))
 * [HTTP Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
   ([Event Examples](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html))
 * [Application Load Balancer (ALB)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
   ([Event Examples](https://docs.aws.amazon.com/lambda/latest/dg/services-alb.html))
 * [CloudFront Lambda@Edge](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html)
   ([Event Examples](https://docs.aws.amazon.com/lambda/latest/dg/lambda-edge.html))
   
```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from mangum import Mangum

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/")
async def main():
    return "somebigcontent"

handler = Mangum(app, TEXT_MIME_TYPES=["application/vnd.some.type"])
```

## Configuring binary responses

Binary responses are determined using the `Content-Type` and `Content-Encoding` headers from the event request and a list of text MIME types.

### Text MIME types

By default, all response data will be [base64 encoded](https://docs.python.org/3/library/base64.html#base64.b64encode) and include `isBase64Encoded=True` in the response ***except*** the following MIME types:

- `application/json`
- `application/javascript`
- `application/xml`
- `application/vnd.api+json`
- `application/vnd.oai.openapi`

Additionally, any `Content-Type` header prefixed with `text/` is automatically excluded.

### Compression

If the `Content-Encoding` header is set to `gzip` or `br`, then a binary response will be returned regardless of MIME type.

## State machine

The `HTTPCycle` is used by the adapter to communicate message events between the application and AWS. It is a state machine that handles the entire ASGI request and response cycle.

### HTTPCycle

::: mangum.protocols.http.HTTPCycle
    :docstring:
    :members: run receive send

### HTTPCycleState

::: mangum.protocols.http.HTTPCycleState
    :docstring:
