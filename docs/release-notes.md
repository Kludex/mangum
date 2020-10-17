## 0.10.1 (Future release)

* Added CONTRIBUTING.md to outline contribution guidelines.

* Remove deprecated `enable_lifespan` parameter [109](https://github.com/jordaneremieff/mangum/issues/109)

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

* Improve documentation, include CHANGELOG in repo, and include release notes in documentation [#111](https://github.com/jordaneremieff/mangum/pull/111)

* Bugfix lifespan startup behaviour and refactor lifespan cycle, deprecate `enable_lifespan` parameter, document protocols. [#108](https://github.com/jordaneremieff/mangum/pull/108)

## 0.9.0

* Improve documentation [#48](https://github.com/jordaneremieff/mangum/issues/48)

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
