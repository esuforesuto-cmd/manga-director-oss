# v2.4.0 Architecture Summary

```text
Presentation (CLI / local MCP / optional DTO FastAPI / Web UI)
                         |
                         v
Application (Director / Workflow / production and diagnostics composition)
                         |
                         v
Domain <- Ports (Repository / EventBus / Adapter Protocols) <- Infrastructure
```

- Domain remains isolated from workflow delivery, repositories, plugins,
  extensions, providers, backends, and presentation modules.
- The Page `WorkflowEngine` owns legal single-page transitions and event
  publication. It does not import a delivery adapter or concrete repository.
- Project, Chapter, Batch, recovery, integrity, operations, production, and
  reliability services depend on repository ports rather than implementations.
- Provider/Image Backend runtime and production diagnostics are outer facades.
  They do not select Agents, run workflow steps, or mutate workflow state.
- Plugin and Extension code crosses only declared registry/SDK boundaries.
- CLI, FastAPI, MCP, and Web UI are delivery layers. FastAPI returns DTOs only.

Architecture/import gates found no Core-to-Presentation dependency or circular
import. The StateMachine remains the source of truth for every page invariant:
exactly one page per execution, no skipped stage, storyboard before generation,
quality review before approval, and explicit human approval.
