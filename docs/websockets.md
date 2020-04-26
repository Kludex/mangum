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


### S3

```python
handler = Mangum(
    app,
    ws_config={
        "backend": "s3",
        "bucket_name": "connections",
    },
)
```

### Databases (todo)
