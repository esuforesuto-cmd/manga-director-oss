# v5.1 Architecture: Composable Creative Platform

## Architecture decision

v5.1 adds a declarative composition plane above the v5.0 Unified Platform. It
describes available capability contracts and compatible combinations. It is not
an execution plane, plugin loader, persistence layer, or replacement API.

```text
Python API | CLI | FastAPI/REST | MCP | Web UI | Unified SDK
                              |
                  v5.0 Unified Creative API (unchanged)
                              |
          Composition metadata (optional, read-only, declarative)
 Capability Registry | Feature Packs | Platform Profiles | Solution Templates
                              |
 Unified Platform | Context | Runtime | SDK | existing domain services
                              |
 Project | Repository | WorkflowEngine | StateMachine | adapters
```

## Responsibility boundaries

| Element | v5.1 responsibility | Explicitly excluded |
| --- | --- | --- |
| Composable module | Documents a reusable capability boundary and dependencies. | Own domain data or alter service behavior. |
| Feature Pack | Names compatible capability references and evidence requirements. | Install, enable, purchase, or invoke features. |
| Capability Registry | Publishes static capability metadata and compatibility declarations. | Discover remote plugins or load implementations. |
| Platform Profile | Describes a local intended composition. | Change configuration or route execution. |
| Solution Template | Provides a reviewable composition blueprint. | Create projects, tasks, workflows, or approvals. |

## Dependency and compatibility

The composition plane reads public descriptors from Platform Core, SDK, Runtime,
Extensions, and Enterprise modules. Those modules never depend on composition
metadata. Every v5.0 entry point remains first-class and does not require a
capability reference. Future adapters must delegate workflow state changes to
the existing StateMachine and retain one-Page scope.

## Incremental sequence

1. Publish DTO and identifier rules with no runtime integration.
2. Add supplied-metadata validation only.
3. Add optional SDK/presentation discovery after equivalence tests.
4. Consider distribution only after governance, security, and offline
   compatibility review; this planning phase authorizes none of it.
