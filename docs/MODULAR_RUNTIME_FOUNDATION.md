# Modular Runtime Foundation

## Scope

`V48UnifiedPlatformFoundationService.modular_runtime()` returns declarative
module descriptors for Core, Workspace, Agent Platform, Knowledge, Production,
Enterprise, and Decision capabilities. It documents dependency direction; it
does not implement a new Runtime.

## Design boundary

Each `V48RuntimeModuleDTO` records the owner layer, dependency module ids, and
whether Core dependency direction is preserved. All descriptors report
`dynamically_loaded=False` and `runtime_activated=False`.

The existing Runtime, Plugin/Extension SDK, service discovery, imports,
Provider selection, Backend selection, and delivery adapters retain their
current behavior. No module is moved, disabled, dynamically loaded, or
executed by this foundation.

## Compatibility rule

Future modular composition must be opt-in and injected over existing public
services. It cannot change StateMachine authority, workflow stage validation,
one-Page execution, storyboard prerequisites, quality-review prerequisites, or
manual approval.
