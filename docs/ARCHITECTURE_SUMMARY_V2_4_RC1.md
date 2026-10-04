# v2.4.0 RC1 Architecture Summary

```text
Presentation (CLI / local MCP / optional DTO FastAPI / Web UI)
                         |
                         v
Application (Director / Workflow / Production diagnostics composition)
                         |
                         v
Domain <- Ports (Repository / EventBus / Adapter Protocols) <- Infrastructure
```

- Domain imports no workflow, delivery, repository, plugin, extension, or
  adapter module.
- The Page `WorkflowEngine` owns only legal one-page transitions and event
  publication; it imports no delivery adapter or concrete Repository.
- Project, Chapter, Batch, recovery, integrity, operations, and reliability
  helpers use `ProjectRepository` rather than a persistence implementation.
- Provider/Image Backend runtime, Production Runtime, operations, and
  reliability modules are outer diagnostic/application facades. They do not
  select Agents, execute workflow steps, or alter state.
- Plugins and Extensions cross only their declared registry/SDK boundaries.
- CLI, FastAPI, MCP, and Web UI remain Presentation delivery layers and expose
  DTOs rather than Domain model mutation paths.

Architecture/import gates found no Core-to-Presentation dependency or circular
import. StateMachine remains the source of truth for all page invariants.
