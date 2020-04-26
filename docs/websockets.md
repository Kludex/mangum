# WebSockets



## Backends

### SQlite3

...explain that this is for local debugging and should not be in deployments.

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "sqlite3",
        "file_path": "mangum.sqlite3",
        "table_name": "connections",
    },
)
```


### DynamoDB

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "dynamodb",
        "table_name": "connections",
    },
)
```


### S3 (todo)

### Databases (todo)

Refs https://github.com/erm/mangum/issues/52

This decouples the WebSocket support for DynamoDB specifically, allowing multiple storage backends to be defined for WebSocket connections - so far I've added an SQLite backend (to make local debugging easier) in addition to the DynamoDB backend and intend on adding others. There are also a lot of naming/structure changes, but for the most part the HTTP behaviour is completely unchanged other than names.

So the usage currently looks like this:
```python
handler = Mangum(
    app,
    ws_config={
        "backend": "<backend name>",
        ... # required and optional arguments specific to the backend
    },
)
```

