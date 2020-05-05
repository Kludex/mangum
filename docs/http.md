# HTTP

Mangum provides support for [HTTP](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html) and [REST](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html) APIs in API Gateway. The adapter class handles parsing the incoming requests and managing the ASGI cycle.

## Usage

```python
handler = Mangum(app)
```

## Binary support

Binary response support is available depending on the `Content-Type` and `Content-Encoding` headers. The default text mime types are the following:

- `application/json`
- `application/javascript`
- `application/xml`
- `application/vnd.api+json`

All `Content-Type` headers starting with `text/` are included by default.

If the `Content-Encoding` header is set to `gzip`, then a binary response will be returned regardless of mime type.

Binary response bodies will be base64 encoded and `isBase64Encoded` will be `True`.