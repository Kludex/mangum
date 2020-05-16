# HTTP

Mangum provides support for both [REST](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html) and the newer [HTTP](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html) APIs in API Gateway. It also includes configurable binary response support.

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

By default, all response data will be [base64 encoded](https://docs.python.org/3/library/base64.html#base64.b64encode) and include `isBase64Encoded=True` in the response ***except*** the default text MIME types and any MIME types included in the `TEXT_MIME_TYPES` list setting.

The following types are excluded from binary responses by default:

- `application/json`
- `application/javascript`
- `application/xml`
- `application/vnd.api+json`

Additionally, any `Content-Type` header prefixed with `text/` is automatically excluded.

### GZip

If the `Content-Encoding` header is set to `gzip`, then a binary response will be returned regardless of MIME type.

## API

The `HTTPCycle` is used by the adapter to communicate message events between the application and AWS. It is a state machine that handles the entire ASGI request and response cycle.

### HTTPCycle

::: mangum.protocols.http.HTTPCycle
    :docstring:
    :members: run receive send

### HTTPCycleState

::: mangum.protocols.http.HTTPCycleState
    :docstring:
