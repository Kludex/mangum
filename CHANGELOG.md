## 0.9.1

* Refactor lifespan class to be more consistent with other cycle classes and to be more compliant with ASGI spec

* Bugfix lifespan startup behaviour, allow lifespan cycle to be used as a context manager in the adapter [107](https://github.com/erm/mangum/issues/107).

* Deprecate `enable_lifespan` parameter to be replaced by new `lifespan` option

* Include CHANGELOG in repo and release notes in documentation [110](https://github.com/erm/mangum/issues/110)

* Update protocol classes generally with  docstrings/comments/better state transitions/more compliant with ASGI spec.

* Overhaul documentation structure and content.

## 0.9.0

* Improve documentation [#48](https://github.com/erm/mangum/issues/48)

* Resolve issue with `rawQueryString` in HTTP APIs using wrong type [#105](https://github.com/erm/mangum/issues/105)

* Implement new WebSocket storage backends for managing connections (PostgreSQL, Redis, DyanmoDB, S3, SQlite) using a single `dsn` configuration parameter [#100](https://github.com/erm/mangum/issues/100)

## 0.9.0b1 (pre-release)

* Refactor ASGI lifespan handlers and automatically detect if lifespan is supported by an application [#62](https://github.com/erm/mangum/issues/62)

* Decouple WebSocket support from DyanmoDB to allow alternative WebSocket storage backends [#52](https://github.com/erm/mangum/issues/52)

* Implement new WebSocket storage backends for managing connections (PostgreSQL, Redis, DyanmoDB, S3, SQlite)

* Improving logging throughout the various classes