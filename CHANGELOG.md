# Changelog

## [6.3.0](https://github.com/zoharbabin/kaltura-api-guides/compare/v6.2.0...v6.3.0) (2026-04-18)


### New Guides & Features

* **cue-points:** add Cue Points & Interactive Video guide (32 tests) ([8499fa3](https://github.com/zoharbabin/kaltura-api-guides/commit/8499fa3885b1222681e36fa3f455d524a3f42f47))
* **cue-points:** split into hub + 5 dedicated guides ([575b044](https://github.com/zoharbabin/kaltura-api-guides/commit/575b04424a3c9248ec3e9a64e6de9c9a1048263d))
* **genie:** rewrite guide and tests from source code analysis ([58095c8](https://github.com/zoharbabin/kaltura-api-guides/commit/58095c8beafd0f86291cc14036f883dbb9211135))
* **vod-avatar:** rewrite guide with full server-side API and manual storyboard workflow ([d6c49f5](https://github.com/zoharbabin/kaltura-api-guides/commit/d6c49f573c4041601fa66689f2b9b7d8766073d6))


### Fixes & Corrections

* **ci:** shorten commit header for commitlint ([1e0f973](https://github.com/zoharbabin/kaltura-api-guides/commit/1e0f9734ac2b036e4f847e12771b714275e7274e))
* **deploy:** align llms.txt with auto-generation script ([c910862](https://github.com/zoharbabin/kaltura-api-guides/commit/c9108621391da7bfb4f417e1295fcea996c0e2ff))
* **tests:** add retry loop for parent-child index propagation ([8349d96](https://github.com/zoharbabin/kaltura-api-guides/commit/8349d96e5df5f4168f9d8d71e72efa0fbf10e32d))
* **tests:** clean up ep_media_account when empty after event deletion ([a7ba17d](https://github.com/zoharbabin/kaltura-api-guides/commit/a7ba17d41c503f8f0c4c527b0b0ec12677446d37))
* **tests:** filter ready-entry lookup to exclude ephemeral test entries ([e4b9873](https://github.com/zoharbabin/kaltura-api-guides/commit/e4b9873bfe4f88cc7cc1da0361b897585016808c))
* **tests:** generate Genie-specific KS with genieid privilege ([0a087d0](https://github.com/zoharbabin/kaltura-api-guides/commit/0a087d0d615238514dac76c3140d3ffde96767eb))
* **tests:** handle API timing and state edge cases ([87574e7](https://github.com/zoharbabin/kaltura-api-guides/commit/87574e7c91e9d84d3aed4a6c4c152fa53e36340b))
* **tests:** make all test files self-contained and CI-resilient ([561c19f](https://github.com/zoharbabin/kaltura-api-guides/commit/561c19f1235ce5b5c07e3000abcfde75071eb791))
* **tests:** make all test files self-contained and CI-resilient ([ae04cab](https://github.com/zoharbabin/kaltura-api-guides/commit/ae04cab7d260244e48a2a4732959cec489c13699))
* **tests:** prevent cross-test entry deletion race in CI ([e8fc5ea](https://github.com/zoharbabin/kaltura-api-guides/commit/e8fc5eaf7a222405fa5d4fea5c17a46d5510aedc))
* **tests:** proper cleanup for Events Platform + strict Genie search assertions ([6a70134](https://github.com/zoharbabin/kaltura-api-guides/commit/6a7013488be8843b2098098520bb79424638063c))
* **tests:** resolve 5 remaining CI failures for full green suite ([447ba63](https://github.com/zoharbabin/kaltura-api-guides/commit/447ba63e046c2f8541dd56d657cdaf6dd95318f8))
* **tests:** retry on network timeout in kaltura_post helper ([3bbc96d](https://github.com/zoharbabin/kaltura-api-guides/commit/3bbc96d372b7294eef01d8346c5473ca7e284e16))
* **tests:** use content-aware query for Genie /mcp/search tests ([ee7447a](https://github.com/zoharbabin/kaltura-api-guides/commit/ee7447a56d66e4e456e74488ca4fce342c8a51b8))


### Tests

* add 3 REACH tests and update counts to 777 ([7b7b316](https://github.com/zoharbabin/kaltura-api-guides/commit/7b7b31692fb56f4d095d0310aaddbb04b4789e78))
* **cue-points:** add 14 coverage tests (51 total) ([c7185f7](https://github.com/zoharbabin/kaltura-api-guides/commit/c7185f71d886bfe2d6e4988d28f0b02582ec8353))
* **cue-points:** add timedThumbAsset and hotspot tests (32→37) ([93924c3](https://github.com/zoharbabin/kaltura-api-guides/commit/93924c3dd23c251cc1cd9fdede4ff61c2883350e))
