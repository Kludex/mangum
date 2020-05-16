# Frameworks

Mangum is intended to provide support to any [ASGI](https://asgi.readthedocs.io/en/latest/) (*Asynchronous Server Gateway Interface*) application or framework. The ["turtles all the way down"](https://simonwillison.net/2009/May/19/djng/?#turtles-all-the-way-down) principle of ASGI allows for a great deal of interoperability across many different implementations, so the adapter should "just work"* for any ASGI application or framework. 

<small>* if it doesn't, then please open an [issue](https://github.com/erm/mangum/issues). :)</small>

## Background

We can think about the ASGI framework support without referencing an existing implementation. There are no framework-specific rules or dependencies in the adapter class, and all applications will be treated the same.

Let's invent an API for a non-existent microframework to demonstrate things further. This could represent *any* ASGI framework application:

```python
import framework
from mangum import Mangum

app = framework.applications.Application()


@app.route("/")
def endpoint(request: framework.requests.Request) -> dict:
    return {"hi": "there"}


handler = Mangum(app)
```

None of the framework details are important here. The routing decorator, request parameter, and return value of the endpoint method could be anything. The `app` instance will be a valid `app` parameter for Mangum so long as the framework exposes an ASGI-compatible interface:

```python
class Application(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...
```

### Limitations

An application or framework may implement behaviour that is incompatible with the [limitations](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html) of AWS Lambda, and there may be additional configuration required depending on a particular deployment circumstance. In some cases it is possible to work around these limitations, such as how Mangum implements WebSocket [backends](https://mangum.io/websockets/#backends) to persist connection details across instances, but these kinds of limitations should generally be dealt with outside of Mangum itself.

## Frameworks

The examples on this page attempt to demonstrate the most basic implementation of a particular framework (usually from official documentation) to highlight the interaction with Mangum. Specific deployment tooling, infrastructure, external dependencies, etc. are not taken into account.

### Starlette

[Starlette](https://www.starlette.io/) is a lightweight ASGI framework/toolkit, which is ideal for building high performance asyncio services.

Mangum uses it as a toolkit in tests and as an application framework in the [example](https://github.com/erm/mangum-example) project. It is developed by [Encode](https://github.com/encode), a wonderful community and collection of projects that is building the foundations of the Python async web ecosystem.

Define an application:

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from mangum import Mangum


async def homepage(request):
    return JSONResponse({'hello': 'world'})

routes = [
    Route("/", endpoint=homepage)
]

app = Starlette(debug=True, routes=routes)
```

Then wrap it using Mangum:

```python
handler = Mangum(app)
```

### FastAPI

[FastAPI](https://fastapi.tiangolo.com/) is a modern, fast (high-performance), web framework for building APIs with Python 3.6+ based on standard Python type hints. 

```python
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

handler = Mangum(app)
```

### Responder

[Responder](https://responder.readthedocs.io/en/latest) is a familiar HTTP Service Framework for Python, powered by Starlette. The `static_dir` and `templates_dir` parameters must be set to none to disable Responder's automatic directory creation behaviour because AWS Lambda is a read-only file system - see the [limitations](https://mangum.io/asgi/#limitations) section for more details.

```python
from mangum import Mangum
import responder

app = responder.API(static_dir=None, templates_dir=None)


@app.route("/{greeting}")
async def greet_world(req, resp, *, greeting):
    resp.text = f"{greeting}, world!"


handler = Mangum(app)
```

The adapter usage for both FastAPI and Responder is the same as Starlette. However, this may be expected because they are built on Starlette - what about other frameworks?

### Quart

[Quart](https://pgjones.gitlab.io/quart/) is a Python ASGI web microframework. It is intended to provide the easiest way to use asyncio functionality in a web context, especially with existing Flask apps. This is possible as the Quart API is a superset of the Flask API.

```python
from quart import Quart
from mangum import Mangum

app = Quart(__name__)


@app.route("/hello")
async def hello():
    return "hello world!"

handler = Mangum(app)
```

### Sanic

[Sanic](https://github.com/huge-success/sanic) is a Python 3.6+ web server and web framework that's written to go fast. It allows the usage of the async/await syntax added in Python 3.5, which makes your code non-blocking and speedy.

```python
from sanic import Sanic
from sanic.response import json
from mangum import Mangum

app = Sanic()


@app.route("/")
async def test(request):
    return json({"hello": "world"})


handler = Mangum(app)
```

### Django

[Django](https://docs.djangoproject.com/) is a high-level Python Web framework that encourages rapid development and clean, pragmatic design. 

It started introducing ASGI support in version [3.0](https://docs.djangoproject.com/en/3.0/releases/3.0/#asgi-support). Certain async capabilities are not yet implemented and planned for future releases, however it can still be used with Mangum and other ASGI applications at the outer application level.

```python
# asgi.py
import os
from mangum import Mangum
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

application = get_asgi_application()

handler = Mangum(application, lifespan="off")
```

This example looks a bit different than the others because it is based on Django's standard project configuration, but the ASGI behaviour is the same.

### Channels

[Channels](https://channels.readthedocs.io/en/latest/) is a project that takes Django and extends its abilities beyond HTTP - to handle WebSockets, chat protocols, IoT protocols, and more. It is the original driving force behind the ASGI specification.

It currently does [not](https://github.com/django/channels/issues/1319
) support ASGI version 3, but you can convert the application from ASGI version 2 using the `guarantee_single_callable` method provided in [asgiref](https://github.com/django/asgiref).

```python
# asgi.py
import os
import django
from channels.routing import get_default_application
from asgiref.compatibility import guarantee_single_callable
from mangum import Mangum


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()
application = get_default_application()

wrapped_application = guarantee_single_callable(application)
handler = Mangum(wrapped_application, lifespan="off")
```
