# Lifespan

Mangum supports the ASGI [Lifespan](https://asgi.readthedocs.io/en/latest/specs/lifespan.html) protocol. This allows applications to define lifespan startup and shutdown event handlers.

```python
from mangum import Mangum
from fastapi import FastAPI

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    pass


@app.on_event("shutdown")
async def shutdown_event():
    pass


@app.get("/")
def read_root():
    return {"Hello": "World"}

handler = Mangum(app, lifespan="auto")
```

## Configuring Lifespan events

Lifespan support is automatically determined unless explicitly turned on or off. A string value option is used to configure lifespan support, the choices are `auto`, `on`, and `off`. 

### Options

- **auto**
    
    Application support for lifespan **is inferred** using the state transitions. Any error that occurs during startup will be logged and the ASGI application cycle will continue unless a `lifespan.startup.failed` event is sent.

- **on**
    
    Application support for lifespan **is explicit**. Any error that occurs during startup will be raised and a 500 response will be returned.

- **off**
    
    Application support for lifespan **is ignored**. The application will not enter the lifespan cycle context.

Defaults to `auto`.

## API

The `LifespanCycle` is a state machine that handles ASGI `lifespan` events intended to run before and after HTTP and WebSocket requests are handled. 

### LifespanCycle

::: mangum.protocols.lifespan.LifespanCycle
    :docstring:
    :members: run receive send startup shutdown 

#### Context manager

Unlike the `HTTPCycle` and `WebSocketCycle` classes, the `LifespanCycle` is also used as a context manager in the adapter class. If lifespan support is turned off, then the application never enters the lifespan cycle context.

```python
 with ExitStack() as stack:
    # Ignore lifespan events entirely if the `lifespan` setting is `off`.
    if self.lifespan in ("auto", "on"):
        asgi_cycle: typing.ContextManager = LifespanCycle(
            self.app, self.lifespan
        )
        stack.enter_context(asgi_cycle)
```

The magic methods `__enter__` and `__exit__` handle running the async tasks that perform startup and shutdown functions.

```python
    def __enter__(self) -> None:
        """
        Runs the event loop for application startup.
        """
        self.loop.create_task(self.run())
        self.loop.run_until_complete(self.startup())

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_value: typing.Optional[BaseException],
        traceback: typing.Optional[types.TracebackType],
    ) -> None:
        """
        Runs the event loop for application shutdown.
        """
        self.loop.run_until_complete(self.shutdown())
```

### LifespanCycleState

::: mangum.protocols.lifespan.LifespanCycleState
    :docstring:

