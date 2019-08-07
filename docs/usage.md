# Usage

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