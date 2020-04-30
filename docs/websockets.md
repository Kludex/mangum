# WebSockets

Mangum provides support for [WebSocket API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html) events in API Gateway. The adapter class handles parsing the incoming requests and managing the ASGI cycle using a configured storage backend.

## Events

There are three events that are handled by the adapter:

#### CONNECT

A persistent connection between the client and a WebSocket API is being initiated. The adapter uses a supported WebSocket backend to store the connection id and initial request information.

#### MESSAGE

A connected client has sent a message. The adapter will retrieve the initial request information from the backend using the connection id to form the ASGI connection `scope` and run the ASGI application cycle.

#### DISCONNECT

The client or the server disconnects from the API. The adapter will remove the connection from the backend.


## Backends

A data store, such as a cloud database, is required in order to persist the connection identifiers in a 'serverless' environment. Any data store can be used as long as it is accessible remotely to the AWS Lambda function.

All supported backends require a `ws_config` configuration mapping. The configuration must contain the identifier for a backend along with any additional required arguments for the selected backend:

```python
mangum = Mangum(app, ws_config={"sqlite3": ...})
```

The following backends are currently supported:

 - `dynamodb`
 - `s3`
 - `sqlite3` (for local debugging)


Optional configuration arguments:

- `api_gateway_endpoint_url`


### DynamoDB

The `DynamoDBStorageBackend` uses a [DynamoDB](https://aws.amazon.com/dynamodb/) table to store the connection details.

#### Configuration

- `table_name` : **str** *(required)*

    The name of the table in DynamoDB.
    
- `endpoint_url`: **str**

    The endpoint url to use in DynamoDB calls. This is useful if you are debugging locally with a package such as [serverless-dynamodb-local](https://github.com/99xt/serverless-dynamodb-local).

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "dynamodb",
        "table_name": "connections",
    },
)
```


### S3

The `S3StorageBackend` uses an (S3)[https://aws.amazon.com/s3/](https://aws.amazon.com/s3/)] bucket as a key-value store to store the connection details.

#### Configuration

- `bucket_name` : **str** *(required)*
    
    The name of the bucket in S3.

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "s3",
        "bucket_name": "connections",
    },
)
```

### SQlite3

The `sqlite3` backend uses a local [sqlite3](https://docs.python.org/3/library/sqlite3.html) database to store connection. It is intended for ***local*** debugging (with a package such as [Serverless Offline](https://github.com/dherault/serverless-offline)) and will ***not*** work in an AWS Lambda deployment.

#### Configuration

- `file_path` : **str** *(required)*

    The file name or path to a sqlite3 file. If one does not exist, then it will be created automatically.

- `table_name` : **str** (default=`"connection"`)

    The name of the table to use for the connections in an sqlite3 database.
 
```python
handler = Mangum(
    app,
    ws_config={
        "backend": "sqlite3",
        "file_path": "mangum.sqlite3",
        "table_name": "connection",
    },
)
```

### Other Databases (todo)
