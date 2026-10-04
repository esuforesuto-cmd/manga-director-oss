# v2.2 Iteration 2 Runtime Improvement Report

## Outcome

Iteration 2 improves Plugin, Extension SDK, EventBus, Configuration, and
operational diagnostics while retaining the existing Core Architecture and
version (`2.1.0`). No required public Protocol, workflow transition, or
repository contract changed.

## Delivered

| Boundary | Improvement | Compatibility result |
| --- | --- | --- |
| Plugin Runtime | Change-aware discovery/manifest cache, factory cache, dependency-order cache, initialization timings, and named lazy loading | Existing manifests, Protocol, lifecycle, and `load_enabled()` behavior remain unchanged. |
| Extension SDK | Manifest/compatibility/entry-point cache and deterministic package contents | Existing validator, loader, manifest, and context APIs remain unchanged. |
| EventBus | Cached listener tuples, duplicate-subscription suppression, bounded duplicate-event IDs | Event types and synchronous `publish()`/`subscribe()` signatures remain unchanged. |
| Configuration | File/environment-sensitive validated cache and nested default merge | `load_config()` and `AppConfig` remain compatible; unchanged paths return an immutable cached instance. |
| Diagnostics | Safe system, Plugin, Extension, Configuration, Repository, EventBus, and performance report composition | Diagnostics remain passive and do not affect workflow control flow. |

## Verification

- Plugin Runtime, Extension Runtime, EventBus dispatch, Configuration reload,
  Diagnostics, and runtime performance regression tests pass.
- Full suite: 132 passing tests and 84.99% branch coverage (80% gate).
- Ruff and strict mypy pass for source, tests, and benchmarks; wheel/sdist
  packaging succeeds.
- Five provider-free Runtime benchmark scenarios are available under
  `benchmarks/` and guarded by a conservative 8x local regression threshold.
- No asynchronous/distributed EventBus, remote Plugin/Extension, Cloud Config,
  new Workflow, Provider, or breaking API was added.

## Architecture difference review

- Runtime caches stay in application/infrastructure adapters; Domain and the
  Page StateMachine are unchanged.
- Plugin discovery still performs no code imports. Explicit lazy loading invokes
  only the requested enabled Plugin plus its declared dependencies.
- EventBus remains synchronous and in-memory; duplicate suppression is bounded
  by its configurable in-memory event-ID window.
- Configuration snapshots expose cache counts only; diagnostics never include
  secret values or configuration payloads.
