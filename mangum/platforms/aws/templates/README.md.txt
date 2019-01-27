# {{ context.project_name }}

A boilerplate ASGI application for AWS Lambda + API Gateway.

## Deployment

Mangum wraps a few AWS-CLI commands to use the generated settings and template file:

```shell
$ mangum package
```

Then run to deploy:

```shell
$ managum deploy
```

You may also run:

```shell
$ mangum describe
```

to echo the API endpoints to the console.