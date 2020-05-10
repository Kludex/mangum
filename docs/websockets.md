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

All supported backends require a `dsn` connection string argument to configure the connection. Backends that already support connection strings, such as PostgreSQL and Redis, can use their existing syntax. Other backends, such as S3 and DynamoDB, are parsed with a custom syntax defined in the backend class.

```python
handler = Mangum(app, dsn="[postgresql|redis|dynamodb|s3|sqlite]://[...]")
```

The following backends are currently supported:

 - `dynamodb`
 - `s3`
 - `postgresql`
 - `redis`
 - `sqlite` (for local debugging)

### DynamoDB

The `DynamoDBBackend` uses a [DynamoDB](https://aws.amazon.com/dynamodb/) table to store the connection details.

#### Usage

```python
handler = Mangum(
    app,
    dsn="dynamodb://mytable"
)
```

##### Parameters

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

### S3

The `S3Backend` uses an [S3](https://aws.amazon.com/s3/) bucket as a key-value store to store the connection details.

#### Usage

```python
handler = Mangum(
    app,
    dsn="s3://my-bucket-12345"
)
```

##### Parameters

The S3 backend `dsn` uses the following connection string syntax:

```
s3://<bucket>[/key/...][?region=<region-name>]
```

- `bucket` (Required)
    
    The name of the bucket in S3.

- `region_name`
    
    The region name of the S3 bucket.

### PostgreSQL

The `PostgreSQLBackend` requires [psycopg2](https://github.com/psycopg/psycopg2) and access to a remote PostgreSQL database.

#### Usage

```python
handler = Mangum(
    app,
    dsn="postgresql://myuser:mysecret@my.host:5432/mydb"
)
```

##### Parameters

The PostgreSQL backend `dsn` uses the following connection string syntax:

```
postgresql://[user[:password]@][host][:port][,...][/dbname][?param1=value1&...]
```

- `host` (Required)

    The network location of the PostgreSQL database

Read more about the supported uri schemes and additional parameters [here](https://www.postgresql.org/docs/10/libpq-connect.html#LIBPQ-CONNSTRING).

### Redis

The `RedisBackend` requires [redis-py](https://github.com/andymccurdy/redis-py) and access to a Redis server.

#### Usage

```python
handler = Mangum(
    app,
    dsn="redis://:mysecret@my.host:6379/0"
)
```

#### Parameters

The Redis backend `dsn` uses the following connection string syntax:

```
redis://[[user:]password@]host[:port][/database]
```

- `host` (Required)
    
    The network location of the Redis server.

Read more about the supported uri schemes and additional parameters [here](https://www.iana.org/assignments/uri-schemes/prov/redis).

### SQLite

The `sqlite` backend uses a local [sqlite3](https://docs.python.org/3/library/sqlite3.html) database to store connection. It is intended for ***local*** debugging (with a package such as [Serverless Offline](https://github.com/dherault/serverless-offline)) and will ***not*** work in an AWS Lambda deployment.

#### Usage

```python
handler = Mangum(
    app,
    dsn="sqlite://mydbfile.sqlite3"
)
```

#### Parameters

The SQLite backend uses the following connection string syntax:

```
sqlite://[file_path].db
```

- `file_path` (Required)

    The file name or path to an sqlite3 database file. If one does not exist, then it will be created automatically.

### Alternative backends

If you'd like to see a specific data source supported as a backend, please open an [issue](https://github.com/erm/mangum/issues).