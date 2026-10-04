# v2.3.0 RC1 Architecture Summary

## Audited dependency direction

```text
Presentation (CLI / local MCP / optional DTO FastAPI / Web UI)
                         |
                         v
Application (Director / Workflow / diagnostics composition)
                         |
                         v
Domain <- Ports (Repository / EventBus / Adapter Protocols) <- Infrastructure
```

- Domain imports no workflow, delivery, repository, plugin, or adapter module.
- The Page `WorkflowEngine` owns transitions and events only; it imports no
  delivery adapter or concrete persistence implementation.
- Project, Chapter, and Batch use `ProjectRepository`, not a concrete store.
- Runtime health and enterprise diagnostics consume injected safe snapshots;
  they do not import the CLI configuration implementation or steer workflow.
- Provider/backend lifecycle helpers remain outside Agent and Workflow code.
- Plugins and Extensions are loaded only at outer composition boundaries.
- The optional FastAPI adapter returns DTOs and depends inward; it exposes no
  Domain model and cannot call Agents directly.

No circular import or Core-to-Presentation dependency was found by the
architecture/import gates. One-page, persisted-storyboard, quality-before-
approval, and explicit-human-approval invariants remain StateMachine-owned.
