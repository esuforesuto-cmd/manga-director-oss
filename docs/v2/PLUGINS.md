# v2 Plugin System Design

## Status, goal, and limits

Phase 11 implements local manifest discovery, dependency ordering, lifecycle
management, a typed registry, local install/remove, and CLI administration.
Plugins extend outer capabilities without receiving authority to bypass domain
invariants. Marketplace discovery, remote install, sandboxing, and hot reload
remain out of scope.

## Plugin contract

A plugin exposes a declarative manifest and a single registration entry point.
The implemented lifecycle contract is:

```python
class Plugin(Protocol):
    name: str
    version: str
    description: str

    def initialize(self) -> None: ...
    def register(self, registry: PluginRegistry) -> None: ...
    def shutdown(self) -> None: ...
```

`plugin.yaml` contains the plugin `name`, `version`, `description`,
`entry_point`, `dependencies`, and `enabled` flag. Registration is deterministic
and side-effect free apart from adding declared extensions to the provided
registry.

## Extension points

| Capability | Registration target | Rule |
| --- | --- | --- |
| Agent | agent registry / named agent factory | must return the common `AgentResult`; page transition authority stays in the engine |
| Workflow | `WorkflowPolicy` registry | may define a new named higher-level workflow, never overwrite the default page state machine |
| Repository | repository factory | implements a versioned repository port and serializer compatibility contract |
| Image generator | `ImageGeneratorFactory` registry | exposes the existing minimum image contract or a documented extended sibling port |
| Prompt template | template registry | Markdown template plus metadata and version, no executable template code |
| Event bus | event-bus factory | preserves the canonical event envelope and delivery semantics declaration |
| CLI command | command provider registry | maps input to an application use case; contains no transition logic |

Every registration name is namespaced as `plugin_id:name`. Built-ins retain their stable names. Duplicate names, unsupported API versions, undeclared capabilities, and attempts to replace a protected built-in fail at startup.

## Registry ownership

The CLI composition root owns `PluginRegistry` and the existing factories. It
applies active image-generator builders to `ImageGeneratorFactory` and maps
declared agent contributions to the existing engine mappings. Agents, workflow
engines, domain models, and adapters never discover plugins themselves. This
retains deterministic tests and makes a plugin set part of application
configuration and audit metadata.

## Lifecycle and safety

1. Read manifests without importing plugin code.
2. Resolve enabled dependencies and reject cycles before activation.
3. Load the configured `module:attribute` entry point.
4. Invoke `initialize()`, then `register(registry)`.
5. Use contributions through outer composition; on shutdown, unregister and
   invoke `shutdown()` in reverse load order.

Plugins are untrusted integration code. v2 must document process isolation, least-privilege credentials, timeout/resource limits, and a failure policy before remote or third-party plugins are enabled. A plugin error is a typed application error and must not advance a page state.

## Versioning and tests

The current local plugin contract is tested with fixture plugins for discovery,
loading, lifecycle, dependency errors, registry operations, and Agent/Image
Generator composition. A separately versioned plugin API and capability
negotiation remain required before third-party/remote plugin ecosystems are
enabled.
