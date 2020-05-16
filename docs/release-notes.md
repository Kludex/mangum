# Release Notes

## 0.9.0

* Improve documentation [#48](https://github.com/erm/mangum/issues/48)

* Resolve issue with `rawQueryString` in HTTP APIs using wrong type [#105](https://github.com/erm/mangum/issues/105)

* Implement new WebSocket storage backends for managing connections (PostgreSQL, Redis, DyanmoDB, S3, SQlite) using a single `dsn` configuration parameter [#100](https://github.com/erm/mangum/issues/100)

## 0.9.0b1 (pre-release)

* Refactor ASGI lifespan handlers and automatically detect if lifespan is supported by an application [#62](https://github.com/erm/mangum/issues/62)

* Decouple WebSocket support from DyanmoDB to allow alternative WebSocket storage backends [#52](https://github.com/erm/mangum/issues/52)

* Implement new WebSocket storage backends for managing connections (PostgreSQL, Redis, DyanmoDB, S3, SQlite)

* Improving logging throughout the various classes