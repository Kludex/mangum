# WebSockets

Mangum provides support for [WebSocket API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html) events in API Gateway. The adapter class handles parsing the incoming requests and managing the ASGI cycle using a configured storage backend.

```python
import os

from mangum import Mangum
from starlette.templating import Jinja2Templates
from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint, HTTPEndpoint
from starlette.routing import Route, WebSocketRoute


DSN_URL = os.environ["DSN_URL"]
WEBSOCKET_URL = os.environ["WEBSOCKET_URL"]
HTML = b"""
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("%s");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }


        </script>
    </body>
</html>
""" % WEBSOCKET_URL


class Homepage(HTTPEndpoint):
    async def get(self, request):
        return HTMLResponse(html)


class Echo(WebSocketEndpoint):
    encoding = "text"

    async def on_receive(self, websocket, data):
        await websocket.send_text(f"Message text was: {data}")


routes = [
    Route("/", Homepage),
    WebSocketRoute("/ws", Echo)
]

app = Starlette(routes=routes)
handler = Mangum(app, dsn=DSN_URL)
```

## Configuring a storage backend

A data source is required in order to persist the WebSocket client connections stored in API Gateway*. Any data source can be used as long as it is accessible remotely to the AWS Lambda function. All supported backends require a `dsn` connection string argument to configure the connection between the adapter and the data source. 

```python
handler = Mangum(app, dsn="[postgresql|redis|dynamodb|s3|sqlite]://[...]")
```

<small>*Read the section on ([handling events in API Gateway](https://mangum.io/websockets/#handling-api-gateway-events) for more information.)</small>

### Supported backends

The following backends are currently supported:

 - `dynamodb`
 - `s3`
 - `postgresql`
 - `redis`
 - `sqlite` (for local debugging)

**Note**: The backend storage implementations offer very minimal configuration for creating, fetching, and deleting connection details and will be improved over time. Any error reports or suggestions regarding these backends are greatly appreciated, feel free to open an [issue](https://github.com/erm/mangum/issues).

#### DynamoDB

The `DynamoDBBackend` uses a [DynamoDB](https://aws.amazon.com/dynamodb/) table to store the connection details.

##### Usage

```python
handler = Mangum(
    app,
    dsn="dynamodb://mytable"
)
```

###### Parameters

The DynamoDB backend `dsn` uses the following connection string syntax:

```
dynamodb://<table_name>[?region=<region-name>&endpoint_url=<url>]
```

- `table_name` (Required)

    The name of the table in DynamoDB.  

- `region_name`
    
    The region name of the DyanmoDB table.

- `endpoint_url`

    The endpoint url to use in DynamoDB calls. This is useful if you are debugging locally with a package such as [serverless-dynamodb-local](https://github.com/99xt/serverless-dynamodb-local).

#### S3

The `S3Backend` uses an [S3](https://aws.amazon.com/s3/) bucket as a key-value store to store the connection details.

##### Usage

```python
handler = Mangum(
    app,
    dsn="s3://my-bucket-12345"
)
```

###### Parameters

The S3 backend `dsn` uses the following connection string syntax:

```
s3://<bucket>[/key/...][?region=<region-name>]
```

- `bucket` (Required)
    
    The name of the bucket in S3.

- `region_name`
    
    The region name of the S3 bucket.

#### PostgreSQL

The `PostgreSQLBackend` requires [psycopg2](https://github.com/psycopg/psycopg2) and access to a remote PostgreSQL database.

##### Usage

```python
handler = Mangum(
    app,
    dsn="postgresql://myuser:mysecret@my.host:5432/mydb"
)
```

###### Parameters

The PostgreSQL backend `dsn` uses the following connection string syntax:

```
postgresql://[user[:password]@][host][:port][,...][/dbname][?param1=value1&...]
```

- `host` (Required)

    The network location of the PostgreSQL database

Read more about the supported uri schemes and additional parameters [here](https://www.postgresql.org/docs/10/libpq-connect.html#LIBPQ-CONNSTRING).

#### Redis

The `RedisBackend` requires [redis-py](https://github.com/andymccurdy/redis-py) and access to a Redis server.

##### Usage

```python
handler = Mangum(
    app,
    dsn="redis://:mysecret@my.host:6379/0"
)
```

##### Parameters

The Redis backend `dsn` uses the following connection string syntax:

```
redis://[[user:]password@]host[:port][/database]
```

- `host` (Required)
    
    The network location of the Redis server.

Read more about the supported uri schemes and additional parameters [here](https://www.iana.org/assignments/uri-schemes/prov/redis).

#### SQLite

The `sqlite` backend uses a local [sqlite3](https://docs.python.org/3/library/sqlite3.html) database to store connection. It is intended for ***local*** debugging (with a package such as [Serverless Offline](https://github.com/dherault/serverless-offline)) and will ***not*** work in an AWS Lambda deployment.

##### Usage

```python
handler = Mangum(
    app,
    dsn="sqlite://mydbfile.sqlite3"
)
```

##### Parameters

The SQLite backend uses the following connection string syntax:

```
sqlite://[file_path].db
```

- `file_path` (Required)

    The file name or path to an sqlite3 database file. If one does not exist, then it will be created automatically.

## API

The `WebSocketCycle` is used by the adapter to communicate message events between the application and WebSocket client connections in API Gateway using a storage backend to persist the connection `scope`. It is a state machine that handles the ASGI request and response cycle for each individual message sent by a client.

### WebSocketCycle

::: mangum.protocols.websockets.WebSocketCycle
    :docstring:
    :members: run receive send 

#### Handling API Gateway events

There are three WebSocket events sent by API Gateway for a WebSocket API connection. Each event requires returning a response immediately, and the information required to create the connection scope is only available in the initial `CONNECT` event. Messages are only sent in `MESSAGE` events that occur after the initial connection is established, and they do not include the details of the initial connect event. Due to the stateless nature of AWS Lambda, a storage backend is required to persist the WebSocket connection details for the duration of a client connection.

##### CONNECT

A persistent connection between the client and a WebSocket API is being initiated. The adapter uses a supported WebSocket backend to store the connection id and initial request information.

##### MESSAGE

A connected client has sent a message. The adapter will retrieve the initial request information from the backend using the connection id to form the ASGI connection `scope` and run the ASGI application cycle.

##### DISCONNECT

The client or the server disconnects from the API. The adapter will remove the connection from the backend.

### WebSocketCycleState

::: mangum.protocols.websockets.WebSocketCycleState
    :docstring:
