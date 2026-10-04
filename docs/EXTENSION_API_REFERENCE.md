# v6.0 Extension API v1.0 Reference

## Frozen Extension surface

`ExtensionFrameworkDTO` identifies an SDK, automation, knowledge,
collaboration, or analytics extension and carries its compatibility label and
capability identifiers. `ExtensionFrameworkReport` returns deterministic,
duplicate-aware compatibility diagnostics.

## Stable SDK imports

Extension authors use the existing runtime SDK rather than the observational
v6.0 DTOs:

```python
from manga_director.sdk import Extension, ExtensionContext, ExtensionLoader
from manga_director.sdk import ExtensionManifest, ExtensionValidator
```

Category base classes such as `WorkflowExtension`, `RepositoryExtension`, and
`MCPToolExtension` are exported from the same package. The Extension Framework
does not replace or wrap this SDK contract.

## Lifecycle authority

The v6.0 Extension Framework never registers, loads, executes, enables,
disables, installs, or removes an Extension. Existing Plugin Registry, Plugin
Manager, manifest, loader, and SDK lifecycle contracts remain authoritative.

## Compatibility

`v5_additive` and `v6_foundation` descriptors are supported. Existing Plugin
and Extension API consumers require no migration, and all v5.x lifecycle
behavior remains unchanged.
