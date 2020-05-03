# WebSockets

Mangum provides support for [WebSocket API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html) events in API Gateway. The adapter class handles parsing the incoming requests and managing the ASGI cycle using a configured storage backend.

## Events

There are WebSocket events sent by API Gateway for a WebSocket API connection. Each event requires returning a response and the initial scope information is only available in connect event, so a storage backend is required to persist the connection details.

#### CONNECT

A persistent connection between the client and a WebSocket API is being initiated. The adapter uses a supported WebSocket backend to store the connection id and initial request information.

#### MESSAGE

A connected client has sent a message. The adapter will retrieve the initial request information from the backend using the connection id to form the ASGI connection `scope` and run the ASGI application cycle.

#### DISCONNECT

The client or the server disconnects from the API. The adapter will remove the connection from the backend.

## Backends

A data source, such as a cloud database, is required in order to persist the connection identifiers in a 'serverless' environment. Any data source can be used as long as it is accessible remotely to the AWS Lambda function.

All supported backends require a `params` configuration mapping. The `ws_config` configuration must contain the name of a backend along with any required `params` for the selected backend.

#### Configuration

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "postgresql|redis|dynamodb|s3|sqlite3",
        "params": {...},
    },
)
```

##### Required

- `ws_config` : **dict**

    Configuration mapping for a supported WebSocket backend.

The following required values need to be defined inside the `ws_config`:

- `backend` : **str** *(required)*

    Name of data source backend to use. 


- `params` : **dict** *(required)*
    
    Parameter mapping of required and optional arguments for the specified backend.

The following backends are currently supported:

 - `dynamodb`
 - `s3`
 - `postgresql`
 - `redis`
 - `sqlite3` (for local debugging)

##### Optional

The following optional values may be defined inside the `ws_config`:

- `api_gateway_endpoint_url` : **str**
    
    The endpoint url to use in API Gateway Management API calls.. This is useful if you are debugging locally with a package such as [serverless-dynamodb-local](https://github.com/99xt/serverless-dynamodb-local).

- `api_gateway_region_name` : **str**
    
    The region name of the API Gateway that is managing the API connections.

### DynamoDB

The `DynamoDBStorageBackend` uses a [DynamoDB](https://aws.amazon.com/dynamodb/) table to store the connection details.

#### Configuration

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "dynamodb",
        "params":{
            "table_name": "connections"
        },
    },
)
```

##### Required

- `table_name` : **str** *(required)*

    The name of the table in DynamoDB.

##### Optional

- `region_name` : **str**
    
    The region name of the DyanmoDB table.

- `endpoint_url`: **str**

    The endpoint url to use in DynamoDB calls. This is useful if you are debugging locally with a package such as [serverless-dynamodb-local](https://github.com/99xt/serverless-dynamodb-local).

### S3

The `S3Backend` uses an (S3)[https://aws.amazon.com/s3/](https://aws.amazon.com/s3/)] bucket as a key-value store to store the connection details.

#### Configuration

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "s3",
        "params": {
            "bucket": "asgi-websocket-connections-12345"
        },
    },
)
```

##### Required

- `bucket` : **str** *(required)*
    
    The name of the bucket in S3.

##### Optional

- `region_name` : **str**
    
    The region name of the S3 bucket.

### PostgreSQL

The `PostgreSQLBackend` requires (psycopg2)[https://github.com/psycopg/psycopg2] and access to a remote PostgreSQL database.

#### Configuration

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "postgresql",
        "params": {
            "database": "mangum",
            "user": "postgres",
            "password": "correct horse battery staple",
            "host": "mydb.12345678910.ap-southeast-1.rds.amazonaws.com"
        },
    },
)
```

##### Required

- `uri`: **str** *(required)*
    The connection string for the remote database.

If a `uri` is not supplied, then the following parameters are required:

- `database` : **str** *(required)*
    
    The name of the database.

- `user` : **str** *(required)*
    
    Postgres user username.

- `password` : **str** *(required)*
    
    Postgres user password.

- `host` : **str** *(required)*
    
    Host for Postgres database connection.

##### Optional

- `port` : **str** (default=`5432`)
    
    Port number for Postgres database connection.

- `connect_timeout` **int** (default=`5`)
    
    Timeout for database connection.

- `table_name` **str (default=`"connection"`)
    
    Table name to use to store WebSocket connections. 

### Redis

The `RedisBackend` requires [redis-py](https://github.com/andymccurdy/redis-py) and access to a Redis server.

#### Configuration

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "redis",
        "params": {
            "host": "my.redis.host",
            "port": 6379
            "password": "correct horse battery staple",
        },
    },
)
```

##### Required

- `host` : **str** *(required)*
    
    Host for Redis server.

##### Optional

- `port` : **str** (default=`6379`)
    
    Port number for Redis server.

- `password` : **str**
    
    Password for Redis server.

### SQlite3

The `sqlite3` backend uses a local [sqlite3](https://docs.python.org/3/library/sqlite3.html) database to store connection. It is intended for ***local*** debugging (with a package such as [Serverless Offline](https://github.com/dherault/serverless-offline)) and will ***not*** work in an AWS Lambda deployment.

#### Configuration

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "sqlite3",
        "params": {
            "file_path": "mangum.sqlite3",
            "table_name": "connection",
        },
    },
)
```

##### Required

- `file_path` : **str** *(required)*

    The file name or path to a sqlite3 file. If one does not exist, then it will be created automatically.

##### Optional

- `table_name` : **str** (default=`"connection"`)

    The name of the table to use for the connections in an sqlite3 database.

### Alternative backends

If you'd like to see a specific data source supported as a backend, please open an [issue](https://github.com/erm/mangum/issues).