# Usage


Signature: `Response(content, status_code=200, headers=None, media_type=None)`

* `content` - A string or bytestring.
* `status_code` - An integer HTTP status code.
* `headers` - A dictionary of strings.
* `media_type` - A string giving the media type. eg. "text/html"

Starlette will automatically include a Content-Length header. It will also
include a Content-Type header, based on the media_type and appending a charset
for text types.

Once you've instantiated a response, you can send it by calling it as an
ASGI application instance.



The adapter class `Mangum` accepts the following optional arguments:

- `debug` : bool (default=False)
    
    Enable a simple error response if an unhandled exception is raised in the adapter.


- `spec_version` : int (default=3)
    
    Set the ASGI specification version. ASGI 3 uses a single-callable, ASGI 2 uses a double-callable.

- `enable_lifespan` : bool (default=True)
    
    Specify whether or not to enable lifespan support.

### Example

```python3
from mangum import Mangum

async def app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


handler = Mangum(app, enable_lifespan=False) # disable lifespan for raw ASGI example
```


## Frameworks

Any ASGI framework should work with Mangum, however there are cases where certain non-ASGI behaviour of an application will cause issues when deploying to a serverless platform. You may also need to specify `spec_version=2` for frameworks that do not support the latest ASGI version.
