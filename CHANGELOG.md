# 0.18.0

No changes were made compared to 0.18.0a1.

# 0.18.0a1

* Support Python 3.13 by @Kludex in https://github.com/Kludex/mangum/pull/327

# 0.17.0

* Remove 3.6 reference from frameworks docs by @aminalaee in https://github.com/jordaneremieff/mangum/pull/278
* Add new blog post to external links by @aminalaee in https://github.com/jordaneremieff/mangum/pull/279
* Add exclude_headers parameter by @aminalaee in https://github.com/jordaneremieff/mangum/pull/280

# 0.16.0

* Link to deployment tutorial by @simonw in https://github.com/jordaneremieff/mangum/pull/274
* Added text_mime_types argument by @georgebv in https://github.com/jordaneremieff/mangum/pull/277

# 0.15.1

* Mention that Django works fine too by @WhyNotHugo in https://github.com/jordaneremieff/mangum/pull/261
* Add vnd.oai.openapi to mime type list that are not base64 encoded by @khamaileon in https://github.com/jordaneremieff/mangum/pull/271

# 0.15.0

* Relax type annotations, refactor custom handler inferences, naming by @jordaneremieff in https://github.com/jordaneremieff/mangum/pull/259

# 0.14.1

* Remove references to Python 3.6, update setup.py. by @jordaneremieff in https://github.com/jordaneremieff/mangum/pull/246

## 0.14.0

* Removing Websocket from docs by @aminalaee in https://github.com/jordaneremieff/mangum/pull/241
* Replace abstract handlers, customer handlers, type annotations, refactoring. by @jordaneremieff in https://github.com/jordaneremieff/mangum/pull/242

## 0.13.0

* Remove WebSocket support and misc cleanup/removals by @jordaneremieff in https://github.com/jordaneremieff/mangum/pull/234
* Replace awslambdaric-stubs with new types, refactor import style. by @jordaneremieff in https://github.com/jordaneremieff/mangum/pull/235
* Improve logging by @aminalaee in https://github.com/jordaneremieff/mangum/pull/230

## 0.12.4

* HTTP Gateway V2: Remove use of obsolete multiValueHeaders by @IlyaSukhanov in https://github.com/jordaneremieff/mangum/pull/216
* mypy - Argument "api_gateway_base_path" to "Mangum" has incompatible type "str"; expected "Dict[str, Any]" by @relsunkaev in https://github.com/jordaneremieff/mangum/pull/220
* Added explicit python3.9 and 3.10 support by @relsunkaev in https://github.com/jordaneremieff/mangum/pull/224
* Fix aws_api_gateway handler not accepting combined headers and multiValueHeaders by @Feriixu in https://github.com/jordaneremieff/mangum/pull/229

## 0.12.3

* Fix unhandled `api_gateway_base_path` in `AwsHttpGateway`. [#200](https://github.com/jordaneremieff/mangum/pull/204). Thanks [xpayn](https://github.com/xpayn)!

## 0.12.2

* Exclude `tests/` directory from package. [#200](https://github.com/jordaneremieff/mangum/pull/200). Thanks [bradsbrown](https://github.com/bradsbrown)!

## 0.12.1

* Make `boto3` optional [#197](https://github.com/jordaneremieff/mangum/pull/197).

## 0.12.0

* Reintroduce WebSocket support [#190](https://github.com/jordaneremieff/mangum/pull/190). Thanks [eduardovra](https://github.com/eduardovra)!

* Resolve several issues with ALB/ELB support [#184](https://github.com/jordaneremieff/mangum/pull/184), [#189](https://github.com/jordaneremieff/mangum/pull/189), [#186](https://github.com/jordaneremieff/mangum/pull/186), [#182](https://github.com/jordaneremieff/mangum/pull/182). Thanks [nathanglover](https://github.com/nathanglover) & [jurasofish](https://github.com/jurasofish)!

* Refactor handlers to be separate from core logic [#170](https://github.com/jordaneremieff/mangum/pull/170). Thanks [four43](https://github.com/four43)!

## 0.11.0

* Remove deprecated `enable_lifespan` parameter [#109](https://github.com/jordaneremieff/mangum/issues/109).

* Include API Gateway v2 event cookies in scope headers [#153](https://github.com/jordaneremieff/mangum/pull/153). Thanks [araki-yzrh](https://github.com/araki-yzrh)!

* Support ELB and fix APIGW v2 cookies response [#155](https://github.com/jordaneremieff/mangum/pull/155). Thanks [araki-yzrh](https://github.com/araki-yzrh)!

* Add flake8 to CI checks [#157](https://github.com/jordaneremieff/mangum/pull/157). Thanks [emcpow2](https://github.com/emcpow2)!

* Add type hints for lambda handler context parameter [#158](https://github.com/jordaneremieff/mangum/pull/158).  Thanks [emcpow2](https://github.com/emcpow2)!

* Extract ASGI scope creation into function [#162](https://github.com/jordaneremieff/mangum/pull/162).  Thanks [emcpow2](https://github.com/emcpow2)!

## 0.10.0

* Remove WebSocket support to focus on HTTP [#127](https://github.com/jordaneremieff/mangum/issues/127).

* Support multiValue headers in response [#129](https://github.com/jordaneremieff/mangum/pull/129). Thanks [@koxudaxi](https://github.com/koxudaxi)!

* Fix duplicate test names [#134](https://github.com/jordaneremieff/mangum/pull/134). Thanks [@a-feld](https://github.com/a-feld)!

* Run tests and release package using GitHub Actions [#131](https://github.com/jordaneremieff/mangum/issues/131). Thanks [@simonw](https://github.com/simonw)!

* Only prefix a slash on the api_gateway_base_path if needed [#138](https://github.com/jordaneremieff/mangum/pull/138). Thanks [@dspatoulas](https://github.com/dspatoulas)!

* Add support to Brotli compress [#139](https://github.com/jordaneremieff/mangum/issues/139). Thanks [@fullonic](https://github.com/fullonic)!

## 0.9.2

* Make boto3 dependency optional [#115](https://github.com/jordaneremieff/mangum/pull/115)

## 0.9.1

* Bugfix lifespan startup behaviour and refactor lifespan cycle, deprecate `enable_lifespan` parameter, document protocols. [#108](https://github.com/jordaneremieff/mangum/pull/108)

## 0.9.0

* Resolve issue with `rawQueryString` in HTTP APIs using wrong type [#105](https://github.com/jordaneremieff/mangum/issues/105)

* Implement new WebSocket storage backends for managing connections (PostgreSQL, Redis, DyanmoDB, S3, SQlite) using a single `dsn` configuration parameter [#103](https://github.com/jordaneremieff/mangum/pull/103)

## pre-0.9.0

I did not maintain a CHANGELOG prior to 0.9.0, however, I still would like to include a thank you to following people:

[@lsorber](https://github.com/lsorber)
[@SKalt](https://github.com/SKalt)
[@koxudaxi](https://github.com/koxudaxi)
[@zachmullen](https://github.com/zachmullen)
[@remorses](https://github.com/remorses)
[@allan-simon](https://github.com/allan-simon)
[@jaehyeon-kim](https://github.com/jaehyeon-kim)

Your contributions to previous releases have greatly improved this project and are very much appreciated.

Special thanks to [@tomchristie](https://github.com/tomchristie) for all of his support, encouragement, and guidance early on, and [@rajeev](https://github.com/rajeev) for inspiring this project.
