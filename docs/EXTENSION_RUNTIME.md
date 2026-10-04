# Extension Runtime

`ExtensionValidator` caches compatible manifest files by path, modification
time, size, and Core version. It also caches semantic-version compatibility and
previously verified entry points. Calls to `validate()` and `load()` preserve
their existing return values and validation failures.

`ExtensionContext` remains frozen and intentionally shares supplied Core service
references; the SDK does not duplicate workflow, repository, EventBus, or
factory objects while building a context.

`ExtensionLoader.package()` now writes entries in deterministic order and omits
Python bytecode/cache directories. The package layout and ZIP API are unchanged.

Use `ExtensionValidator.diagnostics()` for safe cache counts, or
`clear_cache()` after a controlled extension deployment. No remote extension,
Marketplace, signature, or sandbox behavior is added.
