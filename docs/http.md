# HTTP

Mangum provides support for [HTTP](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html) and [REST](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html) APIs in API Gateway. The adapter class handles parsing the incoming requests and managing the ASGI cycle.

## Configuration

```python
handler = Mangum(
    app,
    enable_lifespan=True,
    log_level="info",
    api_gateway_base_path=None,
    text_mime_types=None,
)
```

The adapter class accepts the following optional arguments:

- `enable_lifespan` : **bool** (default=`True`)
    
    Specify whether or not to enable lifespan support. The adapter will automatically determine if lifespan is supported by the framework unless explicitly disabled.

- `log_level` : **str** (default=`"info"`)
    
    Level parameter for the logger.

- `api_gateway_base_path` : **str**
    
    Base path to strip from URL when using a custom domain name.

- `text_mime_types` : **list**
        
    The list of MIME types (in addition to the defaults) that should not return binary responses in API Gateway.

## Binary support

Binary response support is available depending on the `Content-Type` and `Content-Encoding` headers. The default text mime types are the following:

- `application/json`
- `application/javascript`
- `application/xml`
- `application/vnd.api+json`

All `Content-Type` headers starting with `text/` are included by default.

If the `Content-Encoding` header is set to `gzip`, then a binary response will be returned regardless of mime type.

Binary response bodies will be base64 encoded and `isBase64Encoded` will be `True`.